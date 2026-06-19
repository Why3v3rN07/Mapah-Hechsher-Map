"""
GET /api/places        – filtered place listing with optional proximity search
GET /api/csrf-token    – issue/refresh CSRF token cookie
"""
import secrets

from flask import request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import (
    Hechshers,
    HechsherAliases,
    PlaceAliases,
    PlaceHechshers,
    PlaceTags,
    Places,
    UserPreferredHechshers,
)
from app.services.geocoding import geocode_forward, geocode_suggestions
from app.utils.security import (
    error_response,
    haversine_miles,
    set_csrf_cookie,
    success,
)
from . import api_bp

_MAX_RADIUS_MI = 10.0
_MAX_RADIUS_KM = 16.09


def _parse_bbox(value: str | None):
    """Parse bbox query param in the format: west,south,east,north."""
    if not value:
        return None
    parts = [p.strip() for p in value.split(",")]
    if len(parts) != 4:
        return "invalid"
    try:
        west, south, east, north = [float(p) for p in parts]
    except (TypeError, ValueError):
        return "invalid"
    if not (-180 <= west <= 180 and -180 <= east <= 180 and -90 <= south <= 90 and -90 <= north <= 90):
        return "invalid"
    if south > north:
        return "invalid"
    return west, south, east, north


# ── CSRF token endpoint ───────────────────────────────────────────────────────

@api_bp.route("/csrf-token", methods=["GET"])
def get_csrf_token():
    """Issue or refresh the CSRF token cookie. Called once on app startup."""
    token = secrets.token_urlsafe(32)
    response, _ = success({"csrf_token": token})
    set_csrf_cookie(response, token)
    return response


# ── Location suggestions ──────────────────────────────────────────────────

@api_bp.route("/locations/search", methods=["GET"])
def search_locations():
    """Search for location suggestions (addresses, cities, neighborhoods)."""
    q = request.args.get("q", "").strip()
    
    if not q:
        return success({"items": []})
    
    suggestions = geocode_suggestions(q, limit=8)
    if suggestions is None:
        # Log detailed error
        import logging
        logger = logging.getLogger(__name__)
        logger.error("Geocoding failed for query: %s", q)
        return error_response("geocoding_unavailable", "Location geocoding is not available. Check MAPBOX_SECRET_TOKEN configuration.", 503)
    
    return success({"items": suggestions})


# ── Places listing ────────────────────────────────────────────────────────────

@api_bp.route("/places/<int:place_id>/aliases", methods=["GET"])
def get_place_aliases(place_id: int):
    place = Places.query.filter_by(place_id=place_id, is_active=True).first()
    if not place:
        return error_response("not_found", "Place not found", 404)

    try:
        aliases = (
            PlaceAliases.query.filter_by(place_id=place_id)
            .order_by(PlaceAliases.place_alias.asc())
            .all()
        )
    except SQLAlchemyError:
        return error_response(
            "schema_outdated",
            "Database schema is missing alias tables. Run database migrations.",
            503,
        )
    return success({"items": [row.place_alias for row in aliases], "count": len(aliases)})


# ── Places listing ────────────────────────────────────────────────────────────

@api_bp.route("/places", methods=["GET"])
def get_places():
    q = request.args.get("q", "").strip()
    # Support hechsher_id, hechsher_id[], and comma-separated values.
    hechsher_ids = request.args.getlist("hechsher_id") or request.args.getlist("hechsher_id[]")
    if len(hechsher_ids) == 1 and "," in hechsher_ids[0]:
        hechsher_ids = [part.strip() for part in hechsher_ids[0].split(",") if part.strip()]
    hechsher_id = None
    if hechsher_ids:
        try:
            hechsher_id = [int(h) for h in hechsher_ids]
        except (ValueError, TypeError):
            return error_response("invalid_query", "hechsher_id must be a valid integer", 400)
    apply_preferred_hechshers = request.args.get("apply_preferred_hechshers", "true").lower() in ("1", "true", "yes")
    hechsher_name = request.args.get("hechsher", "").strip()
    tags = request.args.getlist("tags[]") or request.args.getlist("tags")
    radius = request.args.get("radius", 1.0, type=float)
    unit = request.args.get("unit", "mi")
    lat = request.args.get("lat", type=float)
    lng = request.args.get("lng", type=float)
    location_query = request.args.get("location_query", "").strip()
    bbox_param = request.args.get("bbox", "").strip()
    bbox = _parse_bbox(bbox_param)

    if bbox == "invalid":
        return error_response("invalid_query", "bbox must be west,south,east,north", 400)

    if unit not in ("mi", "km"):
        return error_response("invalid_query", "unit must be 'mi' or 'km'", 400)

    # Enforce max radius
    max_radius = _MAX_RADIUS_MI if unit == "mi" else _MAX_RADIUS_KM
    radius = min(radius, max_radius)
    radius_mi = radius if unit == "mi" else radius / 1.60934

    # Geocode typed location if needed
    if location_query and (lat is None or lng is None):
        coords = geocode_forward(location_query)
        if coords:
            lat, lng = coords

    # If the user is authenticated and no hechsher filter provided,
    # default to their preferred hechshers (spec §2 Map defaults)
    if apply_preferred_hechshers and not hechsher_id and not hechsher_name:
        try:
            verify_jwt_in_request(optional=True)
            user_id = int(get_jwt_identity()) if get_jwt_identity() is not None else None
            if user_id:
                prefs = UserPreferredHechshers.query.filter_by(user_id=user_id).all()
                preferred_ids = [p.hechsher_id for p in prefs]
                if preferred_ids:
                    hechsher_id = preferred_ids  # list handled below
        except Exception:
            pass

    # Base query: active places only
    query = Places.query.filter_by(is_active=True)

    # Hechsher filter
    if isinstance(hechsher_id, list):
        query = (
            query.join(PlaceHechshers)
            .filter(PlaceHechshers.hechsher_id.in_(hechsher_id))
            .distinct()
        )
    elif hechsher_id:
        query = query.join(PlaceHechshers).filter(
            PlaceHechshers.hechsher_id == hechsher_id
        )
    elif hechsher_name:
        query = (
            query.join(PlaceHechshers)
            .join(Hechshers, PlaceHechshers.hechsher_id == Hechshers.hechsher_id)
            .outerjoin(HechsherAliases, Hechshers.hechsher_id == HechsherAliases.hechsher_id)
            .filter(
                or_(
                    Hechshers.hechsher_display_name.ilike(f"%{hechsher_name}%"),
                    HechsherAliases.hechsher_alias.ilike(f"%{hechsher_name}%"),
                )
            )
            .distinct()
        )

    # Name and alias search
    if q:
        query = (
            query.outerjoin(PlaceAliases, Places.place_id == PlaceAliases.place_id)
            .filter(
                or_(
                    Places.place_name.ilike(f"%{q}%"),
                    PlaceAliases.place_alias.ilike(f"%{q}%"),
                )
            )
            .distinct()
        )

    # Optional viewport filter to avoid returning off-screen points.
    if bbox:
        west, south, east, north = bbox
        query = query.filter(Places.latitude.isnot(None), Places.longitude.isnot(None))
        query = query.filter(Places.latitude >= south, Places.latitude <= north)
        if west <= east:
            query = query.filter(Places.longitude >= west, Places.longitude <= east)
        else:
            # Antimeridian-crossing viewport.
            query = query.filter(or_(Places.longitude >= west, Places.longitude <= east))

    # Tag filter
    for tag in tags:
        query = query.filter(
            Places.place_tags.any(PlaceTags.place_tag == tag)
        )

    places = query.all()

    # Proximity filter (post-query since haversine isn't in SQL)
    result = []
    for place in places:
        if lat is not None and lng is not None:
            if place.latitude is None or place.longitude is None:
                continue
            dist_mi = haversine_miles(lat, lng, float(place.latitude), float(place.longitude))
            if dist_mi > radius_mi:
                continue
            dist_out = dist_mi if unit == "mi" else dist_mi * 1.60934
            result.append(place.to_dict(include_distance=dist_out, distance_unit=unit))
        else:
            result.append(place.to_dict())

    return success({"items": result, "count": len(result)})


