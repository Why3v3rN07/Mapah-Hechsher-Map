"""
Security utilities: CSRF double-submit cookie pattern, shared error/response helpers,
admin role guard, and submission rate-limiting key.
"""
import hmac
import secrets
from functools import wraps

from flask import jsonify, request, current_app
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt


# ── Standard JSON responses ───────────────────────────────────────────────────

def success(data: dict, status: int = 200):
    return jsonify(data), status


def error_response(code: str, message: str, status: int, details: dict | None = None):
    body = {"code": code, "message": message}
    if details:
        body["details"] = details
    return jsonify(body), status


# ── CSRF double-submit cookie ─────────────────────────────────────────────────

CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def set_csrf_cookie(response, token: str | None = None):
    """Set (or refresh) the CSRF token cookie on a response object."""
    if token is None:
        token = generate_csrf_token()
    response.set_cookie(
        CSRF_COOKIE_NAME,
        token,
        httponly=False,          # must be readable by JS
        samesite="None",
        secure=True,  #not current_app.debug,
        max_age=30 * 24 * 3600,  # 30 days
        path="/",
    )
    return response, token


def require_csrf(f):
    """Decorator: validate the double-submit CSRF token on state-changing requests."""
    @wraps(f)
    def decorated(*args, **kwargs):
        cookie_val = request.cookies.get(CSRF_COOKIE_NAME)
        header_val = request.headers.get(CSRF_HEADER_NAME)
        if not cookie_val or not header_val:
            return error_response("csrf_missing", "CSRF token required", 403)
        if not hmac.compare_digest(cookie_val, header_val):
            return error_response("csrf_invalid", "Invalid CSRF token", 403)
        return f(*args, **kwargs)
    return decorated


# ── Auth / role guards ────────────────────────────────────────────────────────

def jwt_required_guard(f):
    """Decorator: require a valid access JWT (reads from cookie)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except Exception as exc:
            return error_response("unauthorized", str(exc), 401)
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Decorator: require a valid access JWT with admin status."""
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except Exception as exc:
            return error_response("unauthorized", str(exc), 401)
        from app.models import Users
        user = Users.query.get(int(get_jwt_identity()))
        if not user or user.user_status != "admin":
            return error_response("forbidden", "Admin access required", 403)
        return f(*args, **kwargs)
    return decorated


# ── Rate-limit key function for submissions ───────────────────────────────────

def get_submission_rate_key() -> str:
    """
    Priority: authenticated user ID > device cookie > remote IP.
    Matches spec §5.4.7 (device cookie with IP fallback).
    """
    try:
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
        if user_id:
            return f"user:{user_id}"
    except Exception:
        pass

    device_id = request.cookies.get("device_id")
    if device_id:
        return f"device:{device_id}"

    return f"ip:{request.remote_addr}"


# ── Haversine distance ────────────────────────────────────────────────────────

from math import radians, sin, cos, sqrt, atan2


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return distance between two coordinates in miles."""
    R = 3958.8
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


