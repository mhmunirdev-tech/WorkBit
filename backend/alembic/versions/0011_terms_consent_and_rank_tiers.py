"""persist registration consent and rank tier configuration
Revision ID: 0011_terms_rank_tiers
Revises: 0010_auth_token_attempt_count
"""
from datetime import datetime, timezone
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from app.database.base import Base
import app.models.entities

revision = "0011_terms_rank_tiers"
down_revision = "0010_auth_token_attempt_count"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    user_columns = {column["name"] for column in sa.inspect(bind).get_columns("users")}
    if "terms_accepted_at" not in user_columns:
        op.add_column(
            "users",
            sa.Column("terms_accepted_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "terms_version" not in user_columns:
        op.add_column("users", sa.Column("terms_version", sa.String(length=32), nullable=True))
    Base.metadata.tables["rank_tiers"].create(bind=op.get_bind(), checkfirst=True)
    now = datetime.now(timezone.utc)
    rank_tiers = Base.metadata.tables["rank_tiers"]
    if bind.execute(sa.select(rank_tiers.c.id).limit(1)).first() is None:
        op.bulk_insert(
            rank_tiers,
            [
                {"id": str(uuid4()), "name": name, "threshold": threshold, "sort_order": order, "created_at": now, "updated_at": now}
                for name, threshold, order in (
                    ("Starter", 0, 0),
                    ("Bronze", 50, 1),
                    ("Silver", 200, 2),
                    ("Gold", 500, 3),
                )
            ],
        )


def downgrade():
    Base.metadata.tables["rank_tiers"].drop(bind=op.get_bind(), checkfirst=True)
    op.drop_column("users", "terms_version")
    op.drop_column("users", "terms_accepted_at")
