"""
/api/admin/* – admin-only submission review endpoints.

GET  /api/admin/submissions
GET  /api/admin/submissions/<id>
POST /api/admin/submissions/<id>/approve
POST /api/admin/submissions/<id>/reject
"""
from datetime import datetime, timezone

from flask import request

from app.extensions import db
from app.models import Hechshers, HechsherAliases, PlaceAliases, PlaceHechshers, PlaceTags, Places, Submissions
from app.utils.security import admin_required, error_response, require_csrf, success
from . import api_bp


@api_bp.route("/admin/submissions", methods=["GET"])
@admin_required
def list_admin_submissions():
    spam_filter = request.args.get("spam_filter_result")
    admin_status = request.args.get("admin_review_status")
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 50, type=int)
    page_size = min(page_size, 200)

    query = Submissions.query.order_by(Submissions.created_at.desc())

    if spam_filter in ("approved", "flagged"):
        query = query.filter_by(spam_filter_result=spam_filter)
    if admin_status in ("pending_review", "approved", "rejected"):
        query = query.filter_by(admin_review_status=admin_status)
    else:
        # Default to showing only pending submissions
        query = query.filter_by(admin_review_status="pending_review")

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return success({"items": [s.to_dict() for s in items], "count": total})


@api_bp.route("/admin/submissions/<int:submission_id>", methods=["GET"])
@admin_required
def get_admin_submission(submission_id: int):
    submission = Submissions.query.get(submission_id)
    if not submission:
        return error_response("not_found", "Submission not found", 404)
    return success({"submission": submission.to_dict()})


@api_bp.route("/admin/submissions/<int:submission_id>/approve", methods=["POST"])
@require_csrf
@admin_required
def approve_submission(submission_id: int):
    submission = Submissions.query.get(submission_id)
    if not submission:
        return error_response("not_found", "Submission not found", 404)
    if submission.admin_review_status == "approved":
        return error_response("conflict", "Submission already approved", 409)
    if submission.admin_review_status == "rejected":
        return error_response("conflict", "Cannot approve a rejected submission", 409)

    submission.admin_review_status = "approved"

    # Publish to live map if not already published
    if not submission.is_visible:
        payload = submission.payload_json
        sub_type = submission.submission_type

        if sub_type == "new_place":
            place = Places(
                place_name=payload["place_name"],
                street_address=payload.get("street_address"),
                latitude=payload.get("latitude"),
                longitude=payload.get("longitude"),
                is_active=True,
            )
            db.session.add(place)
            db.session.flush()
            for hid in payload.get("hechsher_ids", []):
                db.session.add(PlaceHechshers(place_id=place.place_id, hechsher_id=hid))
            for tag in payload.get("tags", []):
                db.session.add(PlaceTags(place_id=place.place_id, place_tag=tag))
            for alias in payload.get("aliases", []):
                db.session.add(PlaceAliases(place_id=place.place_id, place_alias=alias))
            submission.place_id = place.place_id

        elif sub_type == "edit" and submission.place_id:
            place = Places.query.get(submission.place_id)
            if place:
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
                if "aliases" in payload:
                    PlaceAliases.query.filter_by(place_id=place.place_id).delete()
                    for alias in payload["aliases"]:
                        db.session.add(PlaceAliases(place_id=place.place_id, place_alias=alias))

        elif sub_type == "tag_update" and submission.place_id:
            place = Places.query.get(submission.place_id)
            if place:
                PlaceTags.query.filter_by(place_id=place.place_id).delete()
                for tag in payload.get("tags", []):
                    db.session.add(PlaceTags(place_id=place.place_id, place_tag=tag))

        elif sub_type == "alias_update" and submission.place_id:
            place = Places.query.get(submission.place_id)
            if place:
                PlaceAliases.query.filter_by(place_id=place.place_id).delete()
                for alias in payload.get("aliases", []):
                    db.session.add(PlaceAliases(place_id=place.place_id, place_alias=alias))

        elif sub_type == "hechsher_create":
            hechsher_data = payload.get("hechsher", {})
            existing = None
            if hechsher_data.get("hechsher_id"):
                existing = Hechshers.query.get(hechsher_data["hechsher_id"])
            if not existing:
                existing = Hechshers(
                    hechsher_display_name=hechsher_data.get("hechsher_display_name", ""),
                    hechsher_symbol=hechsher_data.get("hechsher_symbol"),
                )
                db.session.add(existing)
                db.session.flush()
                for alias in hechsher_data.get("aliases", []):
                    db.session.add(HechsherAliases(hechsher_id=existing.hechsher_id, hechsher_alias=alias))
            payload["hechsher"]["hechsher_id"] = existing.hechsher_id
            submission.payload_json = payload

        submission.is_visible = True
        submission.published_at = datetime.now(timezone.utc)

    db.session.commit()
    return success({
        "submission_id": submission_id,
        "admin_review_status": "approved",
        "is_visible": submission.is_visible,
    })


@api_bp.route("/admin/submissions/<int:submission_id>/reject", methods=["POST"])
@require_csrf
@admin_required
def reject_submission(submission_id: int):
    submission = Submissions.query.get(submission_id)
    if not submission:
        return error_response("not_found", "Submission not found", 404)
    if submission.admin_review_status == "rejected":
        return error_response("conflict", "Submission already rejected", 409)

    data = request.get_json() or {}
    reason = data.get("reason", "")

    submission.admin_review_status = "rejected"
    submission.admin_reject_reason = reason
    submission.is_visible = False

    # Revert live map changes if the submission was already published
    if submission.published_at:
        payload = submission.payload_json
        sub_type = submission.submission_type

        if sub_type == "new_place" and submission.place_id:
            place = Places.query.get(submission.place_id)
            if place:
                place.is_active = False  # soft-delete

        elif sub_type in ("edit", "tag_update", "alias_update") and submission.place_id:
            original = payload.get("original")
            place = Places.query.get(submission.place_id)
            if place and original:
                if sub_type == "edit":
                    place.place_name = original.get("place_name", place.place_name)
                    place.street_address = original.get("street_address", place.street_address)
                    place.latitude = original.get("latitude", place.latitude)
                    place.longitude = original.get("longitude", place.longitude)
                    if "hechsher_ids" in original:
                        PlaceHechshers.query.filter_by(place_id=place.place_id).delete()
                        for hid in original["hechsher_ids"]:
                            db.session.add(PlaceHechshers(place_id=place.place_id, hechsher_id=hid))
                # Revert tags for both edit and tag_update
                if "tags" in original:
                    PlaceTags.query.filter_by(place_id=place.place_id).delete()
                    for tag in original["tags"]:
                        db.session.add(PlaceTags(place_id=place.place_id, place_tag=tag))
                if sub_type == "alias_update" and "aliases" in original:
                    PlaceAliases.query.filter_by(place_id=place.place_id).delete()
                    for alias in original["aliases"]:
                        db.session.add(PlaceAliases(place_id=place.place_id, place_alias=alias))
                if sub_type == "edit" and "aliases" in original:
                    PlaceAliases.query.filter_by(place_id=place.place_id).delete()
                    for alias in original["aliases"]:
                        db.session.add(PlaceAliases(place_id=place.place_id, place_alias=alias))

    db.session.commit()
    return success({
        "submission_id": submission_id,
        "admin_review_status": "rejected",
        "is_visible": False,
    })

