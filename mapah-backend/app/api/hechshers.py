"""
GET /api/hechshers/search  – typeahead search by name or alias
"""
from flask import request
from sqlalchemy import or_

from app.models import Hechshers, HechsherAliases
from app.utils.security import error_response, success
from . import api_bp


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

