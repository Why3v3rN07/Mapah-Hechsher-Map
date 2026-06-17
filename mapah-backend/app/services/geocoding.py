"""
Mapbox Geocoding helpers (server-side, uses secret token).
Spec §8 – typed location resolution for proximity search.
"""
import logging
from urllib.parse import quote

import requests
from flask import current_app

logger = logging.getLogger(__name__)

_GEOCODING_BASE = "https://api.mapbox.com/geocoding/v5/mapbox.places"


def geocode_forward(query: str) -> tuple[float, float] | None:
    """
    Convert a text address/location to (lat, lng).
    Returns None if the query could not be resolved.
    """
    token = current_app.config.get("MAPBOX_SECRET_TOKEN", "")
    if not token:
        logger.warning("MAPBOX_SECRET_TOKEN not set – geocoding unavailable.")
        return None

    url = f"{_GEOCODING_BASE}/{quote(query)}.json"
    try:
        resp = requests.get(
            url,
            params={"access_token": token, "limit": 1},
            timeout=5,
        )
        resp.raise_for_status()
        features = resp.json().get("features", [])
        if not features:
            return None
        lng, lat = features[0]["geometry"]["coordinates"]
        return float(lat), float(lng)
    except Exception as exc:
        logger.error("Forward geocoding failed for %r: %s", query, exc)
        return None


def geocode_suggestions(query: str, limit: int = 8) -> list[dict] | None:
    """
    Get a list of location suggestions for autocomplete.
    Returns a list of dicts with 'place_name', 'lat', 'lng' keys.
    Returns None if the query could not be resolved.
    """
    token = current_app.config.get("MAPBOX_SECRET_TOKEN", "")
    if not token:
        logger.warning("MAPBOX_SECRET_TOKEN not set – geocoding unavailable.")
        return None

    url = f"{_GEOCODING_BASE}/{quote(query)}.json"
    try:
        resp = requests.get(
            url,
            params={"access_token": token, "limit": limit},
            timeout=5,
        )
        resp.raise_for_status()
        features = resp.json().get("features", [])
        if not features:
            return []
        
        suggestions = []
        for feature in features:
            lng, lat = feature["geometry"]["coordinates"]
            suggestions.append({
                "place_name": feature.get("place_name", ""),
                "lat": float(lat),
                "lng": float(lng),
            })
        return suggestions
    except Exception as exc:
        logger.error("Geocoding suggestions failed for %r: %s", query, exc)
        return None


def geocode_reverse(lat: float, lng: float) -> str | None:
    """
    Convert (lat, lng) to a human-readable address string.
    Returns None on failure.
    """
    token = current_app.config.get("MAPBOX_SECRET_TOKEN", "")
    if not token:
        return None

    url = f"{_GEOCODING_BASE}/{lng},{lat}.json"
    try:
        resp = requests.get(
            url,
            params={"access_token": token, "limit": 1},
            timeout=5,
        )
        resp.raise_for_status()
        features = resp.json().get("features", [])
        if not features:
            return None
        return features[0].get("place_name")
    except Exception as exc:
        logger.error("Reverse geocoding failed for (%s, %s): %s", lat, lng, exc)
        return None

