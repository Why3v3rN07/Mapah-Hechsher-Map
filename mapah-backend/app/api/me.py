"""
/api/me/* – authenticated user endpoints:
  GET  /api/me/preferences/hechshers
  PUT  /api/me/preferences/hechshers
  GET  /api/me/submissions
"""
from flask import request
from flask_jwt_extended import get_jwt_identity

from app.extensions import db
from app.models import Hechshers, Submissions, UserPreferredHechshers
from app.utils.security import (
    error_response,
    jwt_required_guard,
    require_csrf,
    success,
)
from . import api_bp


@api_bp.route("/me/preferences/hechshers", methods=["GET"])
@jwt_required_guard
def get_hechsher_preferences():
    user_id = int(get_jwt_identity())
    prefs = UserPreferredHechshers.query.filter_by(user_id=user_id).all()
    return success({"hechsher_ids": [p.hechsher_id for p in prefs]})


@api_bp.route("/me/preferences/hechshers", methods=["PUT"])
@require_csrf
@jwt_required_guard
def update_hechsher_preferences():
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}
    hechsher_ids = data.get("hechsher_ids", [])

    if not isinstance(hechsher_ids, list):
        return error_response("validation_error", "hechsher_ids must be an array", 422)

    # Validate all IDs exist
    for hid in hechsher_ids:
        if not Hechshers.query.get(hid):
            return error_response("not_found", f"Hechsher {hid} not found", 404)

    # Replace preferences
    UserPreferredHechshers.query.filter_by(user_id=user_id).delete()
    for hid in hechsher_ids:
        db.session.add(UserPreferredHechshers(user_id=user_id, hechsher_id=hid))

    db.session.commit()
    return success({"hechsher_ids": hechsher_ids, "message": "Preferences saved"})


@api_bp.route("/me/submissions", methods=["GET"])
@jwt_required_guard
def get_my_submissions():
    user_id = int(get_jwt_identity())
    status = request.args.get("status")
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 20, type=int)
    page_size = min(page_size, 100)

    query = Submissions.query.filter_by(submitted_by_user_id=user_id).order_by(
        Submissions.created_at.desc()
    )

    if status:
        # Filter by moderation status
        valid_statuses = {"approved", "flagged", "pending_review", "rejected"}
        if status not in valid_statuses:
            return error_response("validation_error", f"status must be one of {valid_statuses}", 422)
        if status in ("approved", "flagged"):
            query = query.filter_by(spam_filter_result=status)
        else:
            query = query.filter_by(admin_review_status=status)

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return success({
        "items": [s.to_dict() for s in items],
        "count": total,
        "page": page,
        "page_size": page_size,
    })


