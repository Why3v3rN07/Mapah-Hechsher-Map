"""mvp schema expansion

Revision ID: 57d99b1fe753
Revises:
Create Date: 2026-06-15 23:59:53.639015

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "57d99b1fe753"
down_revision = None
branch_labels = None
depends_on = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _columns(inspector, table_name: str) -> set[str]:
    if not _has_table(inspector, table_name):
        return set()
    return {col["name"] for col in inspector.get_columns(table_name)}


def _enum(name: str, values: tuple[str, ...]):
    return sa.Enum(*values, name=name)


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # ------------------------------------------------------------------
    # Baseline core tables (for fresh DBs)
    # ------------------------------------------------------------------
    if not _has_table(inspector, "users"):
        op.create_table(
            "users",
            sa.Column("user_id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_email", sa.String(length=255), nullable=False, unique=True),
            sa.Column("user_name", sa.String(length=50), nullable=False, unique=True),
            sa.Column("user_password", sa.String(length=256), nullable=False),
            sa.Column(
                "user_status",
                _enum("user_status", ("admin", "basic")),
                nullable=False,
                server_default="basic",
            ),
            sa.Column(
                "user_since_date",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )

    if not _has_table(inspector, "hechshers"):
        op.create_table(
            "hechshers",
            sa.Column("hechsher_id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("hechsher_display_name", sa.String(length=100), nullable=False, unique=True),
            sa.Column("hechsher_symbol", sa.String(length=255), nullable=True),
        )

    if not _has_table(inspector, "places"):
        op.create_table(
            "places",
            sa.Column("place_id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("place_name", sa.String(length=100), nullable=False),
            sa.Column("street_address", sa.String(length=255), nullable=True),
            sa.Column("latitude", sa.Numeric(10, 7), nullable=True),
            sa.Column("longitude", sa.Numeric(10, 7), nullable=True),
            sa.Column("date_added", sa.Date(), nullable=False, server_default=sa.text("CURRENT_DATE")),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        )

    if not _has_table(inspector, "hechsher_aliases"):
        op.create_table(
            "hechsher_aliases",
            sa.Column("hechsher_id", sa.Integer(), sa.ForeignKey("hechshers.hechsher_id"), nullable=False),
            sa.Column("hechsher_alias", sa.String(length=100), nullable=False),
            sa.PrimaryKeyConstraint("hechsher_id", "hechsher_alias"),
        )

    if not _has_table(inspector, "place_tags"):
        op.create_table(
            "place_tags",
            sa.Column("place_id", sa.Integer(), sa.ForeignKey("places.place_id"), nullable=False),
            sa.Column(
                "place_tag",
                _enum("place_tag", ("restaurant", "bakery", "store", "cafe", "meat", "dairy", "parve")),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("place_id", "place_tag"),
        )

    if not _has_table(inspector, "place_hechshers"):
        op.create_table(
            "place_hechshers",
            sa.Column("place_id", sa.Integer(), sa.ForeignKey("places.place_id"), nullable=False),
            sa.Column("hechsher_id", sa.Integer(), sa.ForeignKey("hechshers.hechsher_id"), nullable=False),
            sa.Column(
                "place_hechsher_marking_verity",
                _enum("verification_status", ("verified", "pending", "unverified")),
                nullable=True,
            ),
            sa.PrimaryKeyConstraint("place_id", "hechsher_id"),
        )

    # ------------------------------------------------------------------
    # Legacy-safe table/column expansion
    # ------------------------------------------------------------------
    inspector = sa.inspect(bind)
    place_cols = _columns(inspector, "places")
    if _has_table(inspector, "places"):
        if "latitude" not in place_cols:
            op.add_column("places", sa.Column("latitude", sa.Numeric(10, 7), nullable=True))
        if "longitude" not in place_cols:
            op.add_column("places", sa.Column("longitude", sa.Numeric(10, 7), nullable=True))
        if "is_active" not in place_cols:
            op.add_column("places", sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.true()))
            op.alter_column("places", "is_active", server_default=None)

    if not _has_table(inspector, "submissions"):
        op.create_table(
            "submissions",
            sa.Column("submission_id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("submitted_by_user_id", sa.Integer(), sa.ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True),
            sa.Column("place_id", sa.Integer(), sa.ForeignKey("places.place_id", ondelete="SET NULL"), nullable=True),
            sa.Column("submission_type", _enum("submission_type", ("new_place", "tag_update", "edit")), nullable=False),
            sa.Column("payload_json", sa.JSON(), nullable=False),
            sa.Column("spam_filter_result", _enum("spam_filter_result", ("approved", "flagged")), nullable=False),
            sa.Column("admin_review_status", _enum("admin_review_status", ("pending_review", "approved", "rejected")), nullable=False, server_default="pending_review"),
            sa.Column("admin_reject_reason", sa.Text(), nullable=True),
            sa.Column("is_visible", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )

    if not _has_table(inspector, "user_preferred_hechshers"):
        op.create_table(
            "user_preferred_hechshers",
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.user_id"), nullable=False),
            sa.Column("hechsher_id", sa.Integer(), sa.ForeignKey("hechshers.hechsher_id"), nullable=False),
            sa.PrimaryKeyConstraint("user_id", "hechsher_id"),
        )

    if not _has_table(inspector, "refresh_token_families"):
        op.create_table(
            "refresh_token_families",
            sa.Column("family_id", sa.String(length=36), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.user_id"), nullable=False),
            sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        )

    if not _has_table(inspector, "refresh_tokens"):
        op.create_table(
            "refresh_tokens",
            sa.Column("jti", sa.String(length=36), primary_key=True),
            sa.Column("family_id", sa.String(length=36), sa.ForeignKey("refresh_token_families.family_id"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.user_id"), nullable=False),
            sa.Column("used", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        )

    if not _has_table(inspector, "revoked_tokens"):
        op.create_table(
            "revoked_tokens",
            sa.Column("jti", sa.String(length=36), primary_key=True),
            sa.Column("token_type", sa.String(length=10), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.user_id"), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Keep baseline tables intact; remove only tables introduced by this MVP
    # expansion layer so downgrade does not wipe historical core data.
    for table_name in [
        "revoked_tokens",
        "refresh_tokens",
        "refresh_token_families",
        "user_preferred_hechshers",
        "submissions",
    ]:
        if _has_table(inspector, table_name):
            op.drop_table(table_name)
