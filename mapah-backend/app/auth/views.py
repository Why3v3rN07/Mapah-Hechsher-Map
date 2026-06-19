"""
Auth routes: register, login, refresh, logout, change-password, delete-account.

Security model (spec §5.6):
  - Access + refresh JWTs stored in httpOnly cookies.
  - CSRF double-submit cookie validated on all state-changing requests.
  - Refresh token rotation with reuse detection (per-family revocation).
  - Logout revokes current token family; password-change/delete revokes all.
"""
import uuid
from datetime import datetime, timezone

from flask import request, current_app
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_jwt,
    get_jwt_identity,
    set_access_cookies,
    set_refresh_cookies,
    unset_jwt_cookies,
    verify_jwt_in_request,
)

from app.extensions import db
from app.models import (
    RefreshToken,
    RefreshTokenFamily,
    RevokedToken,
    Users,
)
from app.utils.security import (
    error_response,
    generate_csrf_token,
    jwt_required_guard,
    require_csrf,
    set_csrf_cookie,
    success,
)
from . import auth_bp


# ── Helpers ───────────────────────────────────────────────────────────────────

def _issue_token_pair(user_id: int, family_id: str | None = None):
    """
    Create access + refresh token strings and persist the refresh token.
    Returns (access_token_str, refresh_token_str, family_id).
    """
    if family_id is None:
        family_id = str(uuid.uuid4())
        family = RefreshTokenFamily(family_id=family_id, user_id=user_id)
        db.session.add(family)

    subject = str(user_id)
    access_token = create_access_token(
        identity=subject,
        additional_claims={"family_id": family_id},
    )
    refresh_token = create_refresh_token(identity=subject)
    refresh_jti = decode_token(refresh_token)["jti"]

    rt = RefreshToken(jti=refresh_jti, family_id=family_id, user_id=user_id)
    db.session.add(rt)
    return access_token, refresh_token, family_id


def _set_auth_cookies(response, access_token: str, refresh_token: str, csrf_token: str):
    set_access_cookies(response, access_token)
    set_refresh_cookies(response, refresh_token)
    set_csrf_cookie(response, csrf_token)


def _revoke_access_token(jti: str, user_id: int):
    expires = datetime.now(timezone.utc) + current_app.config["JWT_ACCESS_TOKEN_EXPIRES"]
    db.session.add(RevokedToken(jti=jti, token_type="access", user_id=user_id, expires_at=expires))


def _revoke_all_families(user_id: int):
    """Revoke every refresh token family for a user (password change / account deletion)."""
    RefreshTokenFamily.query.filter_by(user_id=user_id, revoked=False).update(
        {"revoked": True, "revoked_at": datetime.now(timezone.utc)}
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@auth_bp.route("/register", methods=["POST"])
@require_csrf
def register():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not username or not email or not password:
        return error_response("validation_error", "username, email and password are required", 422)
    if len(password) < 8:
        return error_response("validation_error", "Password must be at least 8 characters", 422)

    if Users.query.filter_by(user_name=username).first():
        return error_response("conflict", "Username already taken", 409)
    if Users.query.filter_by(user_email=email).first():
        return error_response("conflict", "Email already registered", 409)

    user = Users(user_name=username, user_email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()  # get user_id before issuing tokens

    access_token, refresh_token, _ = _issue_token_pair(user.user_id)
    db.session.commit()

    csrf_token = generate_csrf_token()
    response, status = success(
        {
            "user": user.to_dict(),
            "csrf_token": csrf_token,
            "access_token": access_token,
            "refresh_token": refresh_token,
        },
        201,
    )
    _set_auth_cookies(response, access_token, refresh_token, csrf_token)
    return response, status


@auth_bp.route("/login", methods=["POST"])
@require_csrf
def login():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    user = Users.query.filter_by(user_email=email).first()
    if not user or not user.check_password(password):
        return error_response("unauthorized", "Invalid email or password", 401)

    access_token, refresh_token, _ = _issue_token_pair(user.user_id)
    db.session.commit()

    csrf_token = generate_csrf_token()
    response, status = success(
        {
            "user": user.to_dict(),
            "message": "Logged in",
            "csrf_token": csrf_token,
            "access_token": access_token,
            "refresh_token": refresh_token,
        }
    )
    _set_auth_cookies(response, access_token, refresh_token, csrf_token)
    return response, status


@auth_bp.route("/refresh", methods=["POST"])
@require_csrf
def refresh():
    try:
        verify_jwt_in_request(refresh=True)
    except Exception as exc:
        return error_response("unauthorized", str(exc), 401)

    jwt_data = get_jwt()
    jti = jwt_data["jti"]
    user_id = int(get_jwt_identity())
    family_id = jwt_data.get("family_id")

    # Reuse detection
    token_record = RefreshToken.query.filter_by(jti=jti).first()
    if token_record is None:
        return error_response("unauthorized", "Unknown refresh token", 401)

    if token_record.used:
        # Reuse attack – revoke entire family
        RefreshTokenFamily.query.filter_by(family_id=token_record.family_id).update(
            {"revoked": True, "revoked_at": datetime.now(timezone.utc)}
        )
        db.session.commit()
        resp, status = error_response("unauthorized", "Token reuse detected. Please log in again.", 401)
        unset_jwt_cookies(resp)
        return resp, status

    family = RefreshTokenFamily.query.get(token_record.family_id)
    if family is None or family.revoked:
        return error_response("unauthorized", "Session revoked", 401)

    # Mark old token as used, issue new pair in the same family
    token_record.used = True
    token_record.used_at = datetime.now(timezone.utc)

    access_token, new_refresh_token, _ = _issue_token_pair(user_id, family_id=token_record.family_id)
    db.session.commit()

    new_csrf = generate_csrf_token()
    response, status = success(
        {
            "message": "Token refreshed",
            "csrf_token": new_csrf,
            "access_token": access_token,
            "refresh_token": new_refresh_token,
        }
    )
    set_access_cookies(response, access_token)
    set_refresh_cookies(response, new_refresh_token)
    set_csrf_cookie(response, new_csrf)
    return response, status


@auth_bp.route("/logout", methods=["POST"])
@require_csrf
@jwt_required_guard
def logout():
    jwt_data = get_jwt()
    jti = jwt_data["jti"]
    user_id = int(get_jwt_identity())
    family_id = jwt_data.get("family_id")

    # Revoke current access token
    _revoke_access_token(jti, user_id)

    # Revoke current refresh token family
    if family_id:
        RefreshTokenFamily.query.filter_by(family_id=family_id).update(
            {"revoked": True, "revoked_at": datetime.now(timezone.utc)}
        )

    db.session.commit()

    response, status = success({"message": "Logged out"})
    unset_jwt_cookies(response)
    return response, status


@auth_bp.route("/change-password", methods=["POST"])
@require_csrf
@jwt_required_guard
def change_password():
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}
    current_pw = data.get("current_password", "")
    new_pw = data.get("new_password", "")

    if not current_pw or not new_pw:
        return error_response("validation_error", "current_password and new_password are required", 422)
    if len(new_pw) < 8:
        return error_response("validation_error", "New password must be at least 8 characters", 422)

    user = Users.query.get(user_id)
    if not user or not user.check_password(current_pw):
        return error_response("unauthorized", "Current password is incorrect", 401)

    user.set_password(new_pw)

    # Revoke current access token and all session families
    jti = get_jwt()["jti"]
    _revoke_access_token(jti, user_id)
    _revoke_all_families(user_id)

    db.session.commit()

    response, status = success({"message": "Password changed"})
    unset_jwt_cookies(response)
    return response, status


@auth_bp.route("/account", methods=["DELETE"])
@require_csrf
@jwt_required_guard
def delete_account():
    user_id = int(get_jwt_identity())
    user = Users.query.get(user_id)
    if not user:
        return error_response("not_found", "User not found", 404)

    # Anonymise submissions – nullify ownership ref (ON DELETE SET NULL handles this
    # at DB level but we also do it explicitly for clarity)
    from app.models import Submissions
    Submissions.query.filter_by(submitted_by_user_id=user_id).update(
        {"submitted_by_user_id": None}
    )

    # Revoke all sessions
    jti = get_jwt()["jti"]
    _revoke_access_token(jti, user_id)
    _revoke_all_families(user_id)

    db.session.delete(user)
    db.session.commit()

    response, status = success({"message": "Account deleted"})
    unset_jwt_cookies(response)
    return response, status
