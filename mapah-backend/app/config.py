import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ── Core ──────────────────────────────────────────────────────────────
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "postgresql://localhost/mapah")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── JWT (httpOnly cookies) ─────────────────────────────────────────────
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-dev-secret-change-me")
    JWT_TOKEN_LOCATION = ["cookies", "headers"]
    JWT_ACCESS_COOKIE_NAME = "access_token"
    JWT_REFRESH_COOKIE_NAME = "refresh_token"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_COOKIE_SECURE = os.getenv("JWT_COOKIE_SECURE", "false").lower() == "true"
    JWT_COOKIE_SAMESITE = os.getenv("JWT_COOKIE_SAMESITE", "Lax")
    JWT_COOKIE_CSRF_PROTECT = False    # we implement CSRF ourselves

    # CSRF double-submit cookie policy (separate from flask-jwt cookie policy)
    CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "false").lower() == "true"
    CSRF_COOKIE_SAMESITE = os.getenv("CSRF_COOKIE_SAMESITE", "Lax")

    # ── External Services ─────────────────────────────────────────────────
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODERATION_MODEL = os.getenv(
        "ANTHROPIC_MODERATION_MODEL", "claude-sonnet-4-5"
    )
    ANTHROPIC_MODERATION_FALLBACK_MODELS = os.getenv(
        "ANTHROPIC_MODERATION_FALLBACK_MODELS",
        "claude-3-7-sonnet-latest,claude-3-5-haiku-20241022",
    )
    ANTHROPIC_MODERATION_MAX_TOKENS = int(
        os.getenv("ANTHROPIC_MODERATION_MAX_TOKENS", "200")
    )
    ANTHROPIC_AUTO_APPROVE_WITHOUT_KEY = (
        os.getenv("ANTHROPIC_AUTO_APPROVE_WITHOUT_KEY", "false").lower() == "true"
    )
    ANTHROPIC_MODERATION_RUNTIME_VERSION = os.getenv(
        "ANTHROPIC_MODERATION_RUNTIME_VERSION", "2026-06-18-runtime-v1"
    )
    MAPBOX_SECRET_TOKEN = os.getenv("MAPBOX_SECRET_TOKEN", "")

    # ── Rate Limiting ─────────────────────────────────────────────────────
    RATELIMIT_STORAGE_URI = os.getenv("REDIS_URL", "memory://")
    RATELIMIT_HEADERS_ENABLED = True

    # ── CORS ──────────────────────────────────────────────────────────────
    CORS_ORIGINS = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://localhost:5174,http://127.0.0.1:5173,http://127.0.0.1:5174",
    ).split(",")

    # ── Map Defaults ──────────────────────────────────────────────────────
    DEFAULT_MAP_LAT = 31.7683
    DEFAULT_MAP_LNG = 35.2137

    # ── Upload Storage ────────────────────────────────────────────────────
    HECHSHER_UPLOAD_DIR = os.getenv("HECHSHER_UPLOAD_DIR", "")


class DevelopmentConfig(Config):
    DEBUG = True
    JWT_COOKIE_SECURE = os.getenv("JWT_COOKIE_SECURE", "false").lower() == "true"
    JWT_COOKIE_SAMESITE = os.getenv("JWT_COOKIE_SAMESITE", "Lax")
    CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "false").lower() == "true"
    CSRF_COOKIE_SAMESITE = os.getenv("CSRF_COOKIE_SAMESITE", "Lax")


class ProductionConfig(Config):
    DEBUG = False
    JWT_COOKIE_SECURE = os.getenv("JWT_COOKIE_SECURE", "true").lower() == "true"
    JWT_COOKIE_SAMESITE = os.getenv("JWT_COOKIE_SAMESITE", "None")
    CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "true").lower() == "true"
    CSRF_COOKIE_SAMESITE = os.getenv("CSRF_COOKIE_SAMESITE", "None")


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
