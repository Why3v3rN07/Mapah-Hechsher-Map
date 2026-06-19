"""
SQLAlchemy models – aligned with spec §7 target data model.
"""
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Enum as PgEnum
from sqlalchemy.exc import SQLAlchemyError

from .extensions import db

# ── Enum types ────────────────────────────────────────────────────────────────

place_tag_enum = PgEnum(
    "restaurant", "bakery", "store", "cafe", "meat", "dairy", "parve",
    name="place_tag",
)
verification_status_enum = PgEnum(
    "verified", "pending", "unverified",
    name="verification_status",
)
user_status_enum = PgEnum("admin", "basic", name="user_status")
submission_type_enum = PgEnum(
    "new_place", "tag_update", "edit", "alias_update", "hechsher_create", name="submission_type"
)
spam_filter_result_enum = PgEnum("approved", "flagged", name="spam_filter_result")
admin_review_status_enum = PgEnum(
    "pending_review", "approved", "rejected",
    name="admin_review_status",
)


# ── Core map entities ─────────────────────────────────────────────────────────

class Places(db.Model):
    __tablename__ = "places"

    place_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    place_name = db.Column(db.String(100), nullable=False)
    street_address = db.Column(db.String(255))
    latitude = db.Column(db.Numeric(10, 7))
    longitude = db.Column(db.Numeric(10, 7))
    date_added = db.Column(db.Date, server_default=db.func.current_date())
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    place_hechshers = db.relationship(
        "PlaceHechshers", backref="place", lazy="select", cascade="all, delete-orphan"
    )
    place_tags = db.relationship(
        "PlaceTags", backref="place", lazy="select", cascade="all, delete-orphan"
    )
    place_aliases = db.relationship(
        "PlaceAliases", backref="place", lazy="select", cascade="all, delete-orphan"
    )

    def to_dict(self, include_distance: float | None = None, distance_unit: str = "mi") -> dict:
        aliases = []
        try:
            aliases = [pa.place_alias for pa in self.place_aliases]
        except SQLAlchemyError:
            # Keep place reads functional even when DB schema lags behind code.
            aliases = []

        d = {
            "place_id": self.place_id,
            "place_name": self.place_name,
            "street_address": self.street_address,
            "latitude": float(self.latitude) if self.latitude is not None else None,
            "longitude": float(self.longitude) if self.longitude is not None else None,
            "date_added": self.date_added.isoformat() if self.date_added else None,
            "hechshers": [ph.to_dict() for ph in self.place_hechshers],
            "tags": [pt.place_tag for pt in self.place_tags],
            "aliases": aliases,
        }
        if include_distance is not None:
            d["distance"] = {"value": round(include_distance, 2), "unit": distance_unit}
        return d


class PlaceTags(db.Model):
    __tablename__ = "place_tags"

    place_id = db.Column(db.Integer, db.ForeignKey("places.place_id"), primary_key=True)
    place_tag = db.Column(place_tag_enum, primary_key=True)


class PlaceAliases(db.Model):
    __tablename__ = "place_aliases"

    place_id = db.Column(db.Integer, db.ForeignKey("places.place_id"), primary_key=True)
    place_alias = db.Column(db.String(120), primary_key=True)


class Hechshers(db.Model):
    __tablename__ = "hechshers"

    hechsher_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    hechsher_display_name = db.Column(db.String(100), nullable=False, unique=True)
    hechsher_symbol = db.Column(db.String(255))

    aliases = db.relationship(
        "HechsherAliases", backref="hechsher", lazy="select", cascade="all, delete-orphan"
    )

    def to_dict(self, matched_alias: str | None = None) -> dict:
        d = {
            "hechsher_id": self.hechsher_id,
            "hechsher_display_name": self.hechsher_display_name,
            "hechsher_symbol": self.hechsher_symbol,
        }
        if matched_alias is not None:
            d["matched_alias"] = matched_alias
        return d


class HechsherAliases(db.Model):
    __tablename__ = "hechsher_aliases"

    hechsher_id = db.Column(
        db.Integer, db.ForeignKey("hechshers.hechsher_id"), primary_key=True
    )
    hechsher_alias = db.Column(db.String(100), primary_key=True)


class PlaceHechshers(db.Model):
    __tablename__ = "place_hechshers"

    place_id = db.Column(db.Integer, db.ForeignKey("places.place_id"), primary_key=True)
    hechsher_id = db.Column(
        db.Integer, db.ForeignKey("hechshers.hechsher_id"), primary_key=True
    )
    place_hechsher_marking_verity = db.Column(verification_status_enum)

    hechsher = db.relationship("Hechshers", lazy="joined")

    def to_dict(self) -> dict:
        if self.hechsher:
            return {
                "hechsher_id": self.hechsher_id,
                "hechsher_display_name": self.hechsher.hechsher_display_name,
                "hechsher_symbol": self.hechsher.hechsher_symbol,
            }
        return {"hechsher_id": self.hechsher_id}


# ── Users and preferences ────────────────────────────────────────────────────

class Users(db.Model):
    __tablename__ = "users"

    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_email = db.Column(db.String(255), nullable=False, unique=True)
    user_name = db.Column(db.String(50), nullable=False, unique=True)
    user_password = db.Column(db.String(256), nullable=False)
    user_status = db.Column(user_status_enum, nullable=False, default="basic")
    user_since_date = db.Column(
        db.DateTime(timezone=True), server_default=db.func.now()
    )

    preferred_hechshers = db.relationship(
        "UserPreferredHechshers", backref="user", lazy="select", cascade="all, delete-orphan"
    )
    submissions = db.relationship("Submissions", back_populates="user", lazy="dynamic")
    refresh_token_families = db.relationship(
        "RefreshTokenFamily", backref="user", lazy="dynamic"
    )

    def set_password(self, password: str) -> None:
        self.user_password = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.user_password, password)

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "user_email": self.user_email,
            "user_name": self.user_name,
            "user_status": self.user_status,
            "preferred_hechshers": [p.hechsher_id for p in self.preferred_hechshers],
        }


class UserPreferredHechshers(db.Model):
    __tablename__ = "user_preferred_hechshers"

    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), primary_key=True)
    hechsher_id = db.Column(
        db.Integer, db.ForeignKey("hechshers.hechsher_id"), primary_key=True
    )


# ── Submissions ───────────────────────────────────────────────────────────────

class Submissions(db.Model):
    __tablename__ = "submissions"

    submission_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    submitted_by_user_id = db.Column(
        db.Integer, db.ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    place_id = db.Column(
        db.Integer, db.ForeignKey("places.place_id", ondelete="SET NULL"), nullable=True
    )
    submission_type = db.Column(submission_type_enum, nullable=False)
    payload_json = db.Column(db.JSON, nullable=False)
    spam_filter_result = db.Column(spam_filter_result_enum, nullable=False)
    admin_review_status = db.Column(
        admin_review_status_enum, nullable=False, default="pending_review"
    )
    admin_reject_reason = db.Column(db.Text, nullable=True)
    is_visible = db.Column(db.Boolean, nullable=False, default=False)
    published_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    updated_at = db.Column(
        db.DateTime(timezone=True),
        server_default=db.func.now(),
        onupdate=db.func.now(),
    )

    user = db.relationship(
        "Users", back_populates="submissions", foreign_keys=[submitted_by_user_id]
    )

    @property
    def compute_visibility(self) -> bool:
        if self.admin_review_status == "rejected":
            return False
        return (
            self.spam_filter_result == "approved"
            or self.admin_review_status == "approved"
        )

    def to_dict(self) -> dict:
        payload = self.payload_json or {}
        hechsher_payload = payload.get("hechsher") or {}
        summary = {
            "submission_type": self.submission_type,
            "place_name": payload.get("place_name") or payload.get("original", {}).get("place_name"),
            "street_address": payload.get("street_address"),
            "hechsher_ids": payload.get("hechsher_ids", []),
            "tags": payload.get("tags", []),
            "aliases": payload.get("aliases", []) or hechsher_payload.get("aliases", []),
            "hechsher_display_name": hechsher_payload.get("hechsher_display_name"),
            "reason": payload.get("reason"),
            "changes": payload.get("changes", {}),
        }
        return {
            "submission_id": self.submission_id,
            "submitted_by_user_id": self.submitted_by_user_id,
            "place_id": self.place_id,
            "submission_type": self.submission_type,
            "payload_json": payload,
            "summary": summary,
            "spam_filter_result": self.spam_filter_result,
            "admin_review_status": self.admin_review_status,
            "admin_reject_reason": self.admin_reject_reason,
            "is_visible": self.is_visible,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ── Token management ──────────────────────────────────────────────────────────

class RefreshTokenFamily(db.Model):
    """Tracks families of refresh tokens for rotation + reuse detection."""
    __tablename__ = "refresh_token_families"

    family_id = db.Column(db.String(36), primary_key=True)   # UUID
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    revoked = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    revoked_at = db.Column(db.DateTime(timezone=True), nullable=True)

    tokens = db.relationship("RefreshToken", backref="family", lazy="dynamic")


class RefreshToken(db.Model):
    """Individual refresh tokens within a family."""
    __tablename__ = "refresh_tokens"

    jti = db.Column(db.String(36), primary_key=True)
    family_id = db.Column(
        db.String(36), db.ForeignKey("refresh_token_families.family_id"), nullable=False
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    used = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    used_at = db.Column(db.DateTime(timezone=True), nullable=True)


class RevokedToken(db.Model):
    """Explicit revocation list for access tokens."""
    __tablename__ = "revoked_tokens"

    jti = db.Column(db.String(36), primary_key=True)
    token_type = db.Column(db.String(10), nullable=False)  # 'access' | 'refresh'
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    revoked_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
