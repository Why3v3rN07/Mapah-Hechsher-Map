"""
GET /api/hechshers/search  – typeahead search by name or alias
POST /api/hechshers        – create a hechsher (moderated)
"""
import os
import uuid
from datetime import datetime, timezone

from flask import current_app, request, send_from_directory
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import Hechshers, HechsherAliases, Submissions
from app.services.moderation import classify_submission
from app.utils.security import error_response, require_csrf, success
from . import api_bp

_ALLOWED_ICON_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}


def _hechsher_upload_dir() -> str:
    upload_dir = current_app.config.get("HECHSHER_UPLOAD_DIR") or os.path.join(
        current_app.instance_path, "uploads", "hechshers"
    )
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


def _current_user_id() -> int | None:
    try:
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
        return int(identity) if identity is not None else None
    except Exception:
        return None


def _parse_aliases() -> list[str]:
    raw_items = request.form.getlist("aliases")
    if len(raw_items) == 1 and "," in raw_items[0]:
        raw_items = [part.strip() for part in raw_items[0].split(",")]
    out = []
    seen = set()
    for value in raw_items:
        clean = value.strip()
        if clean and clean.lower() not in seen:
            out.append(clean)
            seen.add(clean.lower())
    return out


def _save_icon_file(icon_file) -> str | None:
    if not icon_file or not icon_file.filename:
        return None
    filename = secure_filename(icon_file.filename)
    if not filename:
        return None
    _, ext = os.path.splitext(filename)
    ext = ext.lower()
    if ext not in _ALLOWED_ICON_EXTENSIONS:
        return None

    upload_dir = _hechsher_upload_dir()
    final_name = f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}{ext}"
    icon_file.save(os.path.join(upload_dir, final_name))
    return f"/api/hechshers/icons/{final_name}"


def _moderate_hechsher_payload(payload: dict) -> dict:
    moderation = classify_submission(payload)
    if not isinstance(moderation, dict):
        return {
            "result": "flagged",
            "reason": "Invalid moderation response",
            "source": "invalid_response",
            "moderation_version": "hechsher-failsafe-v1",
        }

    if moderation.get("result") not in {"approved", "flagged"}:
        moderation["result"] = "flagged"
        moderation["reason"] = "Invalid moderation result value"

    moderation.setdefault("source", "legacy_unknown")
    moderation.setdefault(
        "moderation_version",
        current_app.config.get("ANTHROPIC_MODERATION_RUNTIME_VERSION", "hechsher-failsafe-v1"),
    )

    # Fail closed: do not auto-publish when moderation metadata is missing/legacy.
    if moderation.get("result") == "approved" and moderation.get("source") in {"legacy_unknown", "unknown", ""}:
        moderation["result"] = "flagged"
        moderation["reason"] = "Moderation metadata missing; manual review required"

    return moderation


@api_bp.route("/hechshers/icons/<path:filename>", methods=["GET"])
def get_hechsher_icon(filename: str):
    return send_from_directory(_hechsher_upload_dir(), filename)


@api_bp.route("/hechshers", methods=["GET"])
def list_hechshers():
    """Return all hechshers with their aliases (for preferences and static lists)."""
    rows = Hechshers.query.order_by(Hechshers.hechsher_display_name.asc()).all()
    items = []
    for h in rows:
        d = h.to_dict()
        d["aliases"] = [a.hechsher_alias for a in h.aliases]
        items.append(d)
    return success({"items": items, "count": len(items)})


@api_bp.route("/hechshers/search", methods=["GET"])
def search_hechshers():
    q = request.args.get("q", "").strip()
    if not q:
        return error_response("validation_error", "q is required", 422)

    limit = request.args.get("limit", 10, type=int)
    limit = min(limit, 50)

    # Search display name directly
    name_matches = (
        Hechshers.query.filter(Hechshers.hechsher_display_name.ilike(f"%{q}%"))
        .limit(limit)
        .all()
    )
    name_ids = {h.hechsher_id for h in name_matches}

    # Search aliases
    alias_rows = (
        HechsherAliases.query.filter(HechsherAliases.hechsher_alias.ilike(f"%{q}%"))
        .limit(limit)
        .all()
    )
    alias_map = {}  # hechsher_id -> matched alias string
    for row in alias_rows:
        if row.hechsher_id not in name_ids:
            alias_map[row.hechsher_id] = row.hechsher_alias

    alias_hechshers = []
    if alias_map:
        alias_hechshers = Hechshers.query.filter(
            Hechshers.hechsher_id.in_(list(alias_map.keys()))
        ).all()

    items = [h.to_dict() for h in name_matches]
    for h in alias_hechshers:
        items.append(h.to_dict(matched_alias=alias_map[h.hechsher_id]))

    items = items[:limit]
    return success({"items": items, "count": len(items)})


@api_bp.route("/hechshers", methods=["POST"])
@require_csrf
def create_hechsher():
    name = request.form.get("name", "").strip()
    aliases = _parse_aliases()
    icon_file = request.files.get("icon")

    if not name:
        return error_response("validation_error", "name is required", 422)

    existing = Hechshers.query.filter(Hechshers.hechsher_display_name.ilike(name)).first()
    if existing:
        return error_response("conflict", "Hechsher already exists", 409)

    icon_url = _save_icon_file(icon_file)
    payload = {
        "submission_type": "hechsher_create",
        "hechsher": {
            "hechsher_display_name": name,
            "hechsher_symbol": icon_url,
            "aliases": aliases,
        },
    }

    moderation = _moderate_hechsher_payload(payload)
    payload["moderation"] = moderation
    spam_result = moderation.get("result", "flagged")
    user_id = _current_user_id()

    submission = Submissions(
        submitted_by_user_id=user_id,
        submission_type="hechsher_create",
        payload_json=payload,
        spam_filter_result=spam_result,
        admin_review_status="pending_review",
    )

    hechsher = None
    if spam_result == "approved":
        hechsher = Hechshers(hechsher_display_name=name, hechsher_symbol=icon_url)
        db.session.add(hechsher)
        db.session.flush()
        for alias in aliases:
            db.session.add(HechsherAliases(hechsher_id=hechsher.hechsher_id, hechsher_alias=alias))
        submission.is_visible = True
        submission.published_at = datetime.now(timezone.utc)
        payload["hechsher"]["hechsher_id"] = hechsher.hechsher_id
        submission.payload_json = payload

    db.session.add(submission)
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        return error_response(
            "schema_outdated",
            "Database schema is missing hechsher submission support. Run database migrations.",
            503,
        )

    result_hechsher = hechsher.to_dict() if hechsher else {
        "hechsher_id": None,
        "hechsher_display_name": name,
        "hechsher_symbol": icon_url,
    }
    return success(
        {
            "hechsher": result_hechsher,
            "submission_id": submission.submission_id,
            "spam_filter_result": spam_result,
            "moderation": moderation,
            "message": "Hechsher submitted for review",
        },
        201,
    )


