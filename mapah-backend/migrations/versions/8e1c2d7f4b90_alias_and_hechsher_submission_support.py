"""alias and hechsher submission support

Revision ID: 8e1c2d7f4b90
Revises: 57d99b1fe753
Create Date: 2026-06-18 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "8e1c2d7f4b90"
down_revision = "57d99b1fe753"
branch_labels = None
depends_on = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "place_aliases"):
        op.create_table(
            "place_aliases",
            sa.Column("place_id", sa.Integer(), sa.ForeignKey("places.place_id"), nullable=False),
            sa.Column("place_alias", sa.String(length=120), nullable=False),
            sa.PrimaryKeyConstraint("place_id", "place_alias"),
        )

    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE submission_type ADD VALUE IF NOT EXISTS 'alias_update'")
        op.execute("ALTER TYPE submission_type ADD VALUE IF NOT EXISTS 'hechsher_create'")
    elif _has_table(inspector, "submissions"):
        # SQLite uses CHECK constraints for Enum values; batch alter rewrites the table
        # so alias/hechsher submission types are accepted after migration.
        with op.batch_alter_table("submissions", recreate="always") as batch_op:
            batch_op.alter_column(
                "submission_type",
                existing_type=sa.Enum("new_place", "tag_update", "edit", name="submission_type"),
                type_=sa.Enum(
                    "new_place",
                    "tag_update",
                    "edit",
                    "alias_update",
                    "hechsher_create",
                    name="submission_type",
                ),
                existing_nullable=False,
            )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "place_aliases"):
        op.drop_table("place_aliases")

    # Enum value removal is intentionally omitted because PostgreSQL cannot
    # safely drop enum values in-place without full type recreation.


