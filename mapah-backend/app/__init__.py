import os
import secrets

from flask import Flask, request, send_from_directory
from flask_cors import CORS

from .config import config_by_name
from .extensions import db, jwt, limiter, migrate


def create_app(test_config: dict | None = None) -> Flask:
    env = os.getenv("FLASK_ENV", "default")
    app = Flask(__name__)
    app.config.from_object(config_by_name.get(env, config_by_name["default"]))

    if test_config:
        app.config.update(test_config)

    # ── Extensions ────────────────────────────────────────────────────────
    CORS(
        app,
        resources={r"/*": {"origins": app.config["CORS_ORIGINS"]}},
        supports_credentials=True,
    )
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    limiter.init_app(app)

    # ── JWT token-in-blocklist callback ───────────────────────────────────
    from .models import RefreshToken, RefreshTokenFamily, RevokedToken

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        jti = jwt_payload["jti"]
        token_type = jwt_payload["type"]

        # Check explicit revocation list (access tokens + manually revoked)
        if RevokedToken.query.filter_by(jti=jti).first():
            return True

        # Refresh tokens: validate family is still active
        if token_type == "refresh":
            token = RefreshToken.query.filter_by(jti=jti).first()
            if token is None:
                return True  # unknown token
            family = RefreshTokenFamily.query.get(token.family_id)
            if family is None or family.revoked:
                return True

        return False

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        from flask import jsonify
        return jsonify({"code": "token_expired", "message": "Token has expired"}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        from flask import jsonify
        return jsonify({"code": "invalid_token", "message": str(error)}), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        from flask import jsonify
        return jsonify({"code": "unauthorized", "message": str(error)}), 401

    # ── Device-ID cookie (anonymous rate-limiting key) ─────────────────────
    @app.after_request
    def set_device_id_cookie(response):
        if not request.cookies.get("device_id"):
            device_id = secrets.token_urlsafe(24)
            response.set_cookie(
                "device_id",
                device_id,
                httponly=True,
                samesite="Lax",
                secure=not app.debug,
                max_age=30 * 24 * 3600,
                path="/",
            )
        return response

    @app.route("/instance/uploads/hechshers/<path:filename>", methods=["GET"])
    def serve_legacy_hechsher_icon(filename: str):
        # Backward compatibility for existing DB rows that store /instance/... icon URLs.
        upload_dir = os.path.join(app.instance_path, "uploads", "hechshers")
        return send_from_directory(upload_dir, filename)

    # ── Blueprints ────────────────────────────────────────────────────────
    from .auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")

    from .api import api_bp
    app.register_blueprint(api_bp, url_prefix="/api")

    return app
