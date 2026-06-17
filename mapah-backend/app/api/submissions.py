"""
POST /api/submissions/place   – create / edit a place (anonymous or authenticated)
POST /api/places/<id>/tags    – tag an existing place (anonymous or authenticated)

Submission pipeline (spec §5.4 + §5.5):
  1. Validate rate limit (1/min per user|device|IP).
  2. Run AI moderation via Anthropic.
  3. For tag_update: deterministic tag-consistency check → auto-flag if inconsistent.
  4. Persist Submission record.
  5. If spam_filter_result == "approved": publish immediately to live map.
"""
from datetime import datetime, timezone

from flask import request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from app.extensions import db, limiter
from app.models import (
    Hechshers,
    PlaceHechshers,
    PlaceTags,
    Places,
    Submissions,
)
from app.services.moderation import are_tags_inconsistent, classify_submission
from app.utils.security import (
    error_response,
    get_submission_rate_key,
    require_csrf,
    success,
)
from . import api_bp

_VALID_TAGS = {"restaurant", "bakery", "store", "cafe", "meat", "dairy", "parve"}
_VALID_SUBMISSION_TYPES = {"new_place", "edit", "tag_update"}


def _current_user_id() -> int | None:
    try:
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
        return int(identity) if identity is not None else None
    except Exception:
        return None


def _publish_new_place(payload: dict) -> Places:
    """Create Place + hechshers + tags from a submission payload."""
    place = Places(
        place_name=payload["place_name"],
        street_address=payload.get("street_address"),
        latitude=payload.get("latitude"),
        longitude=payload.get("longitude"),
        is_active=True,
    )
    db.session.add(place)
    db.session.flush()  # get place_id

    for hid in payload.get("hechsher_ids", []):
        db.session.add(PlaceHechshers(place_id=place.place_id, hechsher_id=hid))

    for tag in payload.get("tags", []):
        db.session.add(PlaceTags(place_id=place.place_id, place_tag=tag))

    return place


def _apply_edit(place: Places, payload: dict):
    """Apply an edit submission to an existing place."""
    if "place_name" in payload:
        place.place_name = payload["place_name"]
    if "street_address" in payload:
        place.street_address = payload["street_address"]
    if "latitude" in payload:
        place.latitude = payload["latitude"]
    if "longitude" in payload:
        place.longitude = payload["longitude"]

    if "hechsher_ids" in payload:
        PlaceHechshers.query.filter_by(place_id=place.place_id).delete()
        for hid in payload["hechsher_ids"]:
            db.session.add(PlaceHechshers(place_id=place.place_id, hechsher_id=hid))

    if "tags" in payload:
        PlaceTags.query.filter_by(place_id=place.place_id).delete()
        for tag in payload["tags"]:
            db.session.add(PlaceTags(place_id=place.place_id, place_tag=tag))


def _apply_tag_update(place: Places, payload: dict):
    """Replace place tags with proposed tags from a tag_update submission."""
    PlaceTags.query.filter_by(place_id=place.place_id).delete()
    for tag in payload.get("tags", []):
        db.session.add(PlaceTags(place_id=place.place_id, place_tag=tag))


# ── POST /api/submissions/place ───────────────────────────────────────────────

@api_bp.route("/submissions/place", methods=["POST"])
@require_csrf
@limiter.limit("1 per minute", key_func=get_submission_rate_key, error_message="Rate limit: one submission per minute.")
def submit_place():
    data = request.get_json() or {}
    submission_type = data.get("submission_type")
    user_id = _current_user_id()

    # ── Validate submission type
    if submission_type not in _VALID_SUBMISSION_TYPES:
        return error_response("validation_error", f"submission_type must be one of {_VALID_SUBMISSION_TYPES}", 422)

    # ── Validate required fields
    if submission_type == "new_place":
        required = ["place_name", "street_address", "hechsher_ids", "tags"]
        missing = [f for f in required if not data.get(f)]
        if missing:
            return error_response("validation_error", f"Missing required fields: {missing}", 422)
        if not data.get("hechsher_ids"):
            return error_response("validation_error", "At least one hechsher is required", 422)
        # Validate hechsher IDs exist
        for hid in data["hechsher_ids"]:
            if not Hechshers.query.get(hid):
                return error_response("not_found", f"Hechsher {hid} not found", 404)

    elif submission_type in ("edit", "tag_update"):
        place_id = data.get("place_id")
        if not place_id:
            return error_response("validation_error", "place_id is required for edit/tag_update", 422)
        place = Places.query.filter_by(place_id=place_id, is_active=True).first()
        if not place:
            return error_response("not_found", "Place not found", 404)
        if submission_type == "edit" and user_id is None:
            return error_response("unauthorized", "Login required to edit a place", 401)

    # Validate tags
    invalid_tags = [t for t in data.get("tags", []) if t not in _VALID_TAGS]
    if invalid_tags:
        return error_response("validation_error", f"Invalid tags: {invalid_tags}", 422)

    # ── Build payload snapshot (stored in submission for audit + revert)
    payload_snapshot = {
        "submission_type": submission_type,
        "place_id": data.get("place_id"),
        "place_name": data.get("place_name"),
        "street_address": data.get("street_address"),
        "latitude": data.get("latitude"),
        "longitude": data.get("longitude"),
        "hechsher_ids": data.get("hechsher_ids", []),
        "tags": data.get("tags", []),
        "source": data.get("source", "manual"),
    }

    # Store original state for edit/tag_update (needed for potential revert on rejection)
    if submission_type in ("edit", "tag_update"):
        place = Places.query.get(data["place_id"])
        payload_snapshot["original"] = {
            "place_name": place.place_name,
            "street_address": place.street_address,
            "latitude": float(place.latitude) if place.latitude else None,
            "longitude": float(place.longitude) if place.longitude else None,
            "hechsher_ids": [ph.hechsher_id for ph in place.place_hechshers],
            "tags": [pt.place_tag for pt in place.place_tags],
        }

    # ── AI moderation
    existing_tags = payload_snapshot["original"]["tags"] if "original" in payload_snapshot else None
    moderation = classify_submission(payload_snapshot, existing_tags=existing_tags)
    spam_result = moderation.get("result", "flagged")

    # ── Create submission record
    submission = Submissions(
        submitted_by_user_id=user_id,
        submission_type=submission_type,
        payload_json=payload_snapshot,
        spam_filter_result=spam_result,
        admin_review_status="pending_review",
    )

    # ── Publish immediately if approved
    published = False
    if spam_result == "approved":
        if submission_type == "new_place":
            new_place = _publish_new_place(payload_snapshot)
            submission.place_id = new_place.place_id
        elif submission_type == "edit":
            _apply_edit(place, payload_snapshot)
            submission.place_id = place.place_id
        elif submission_type == "tag_update":
            _apply_tag_update(place, payload_snapshot)
            submission.place_id = place.place_id

        submission.is_visible = True
        submission.published_at = datetime.now(timezone.utc)
        published = True

    db.session.add(submission)
    db.session.commit()

    return success(
        {
            "submission": submission.to_dict(),
            "published": published,
            "message": "Submitted successfully",
        },
        201,
    )


# ── POST /api/places/<id>/tags ─────────────────────────────────────────────────

@api_bp.route("/places/<int:place_id>/tags", methods=["POST"])
@require_csrf
@limiter.limit("1 per minute", key_func=get_submission_rate_key, error_message="Rate limit: one submission per minute.")
def tag_place(place_id: int):
    place = Places.query.filter_by(place_id=place_id, is_active=True).first()
    if not place:
        return error_response("not_found", "Place not found", 404)

    data = request.get_json() or {}
    proposed_tags = data.get("tags", [])
    reason = data.get("reason", "")

    if not proposed_tags:
        return error_response("validation_error", "tags array is required", 422)

    invalid_tags = [t for t in proposed_tags if t not in _VALID_TAGS]
    if invalid_tags:
        return error_response("validation_error", f"Invalid tags: {invalid_tags}", 422)

    existing_tags = [pt.place_tag for pt in place.place_tags]
    user_id = _current_user_id()

    payload_snapshot = {
        "submission_type": "tag_update",
        "place_id": place_id,
        "tags": proposed_tags,
        "reason": reason,
        "original": {"tags": existing_tags},
    }

    # Deterministic auto-flag for inconsistent tags
    if are_tags_inconsistent(existing_tags, proposed_tags):
        spam_result = "flagged"
    else:
        moderation = classify_submission(payload_snapshot, existing_tags=existing_tags)
        spam_result = moderation.get("result", "flagged")

    submission = Submissions(
        submitted_by_user_id=user_id,
        place_id=place_id,
        submission_type="tag_update",
        payload_json=payload_snapshot,
        spam_filter_result=spam_result,
        admin_review_status="pending_review",
    )

    published = False
    if spam_result == "approved":
        _apply_tag_update(place, payload_snapshot)
        submission.is_visible = True
        submission.published_at = datetime.now(timezone.utc)
        published = True

    db.session.add(submission)
    db.session.commit()

    return success({"submission": submission.to_dict(), "published": published}, 201)


