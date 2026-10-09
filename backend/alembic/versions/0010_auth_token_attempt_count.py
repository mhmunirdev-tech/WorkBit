"""track failed attempts for one-time verification codes
Revision ID: 0010_auth_token_attempt_count
Revises: 0009_dashboard_banners
"""

from alembic import op
from sqlalchemy import Column, Integer, inspect

revision = "0010_auth_token_attempt_count"
down_revision = "0009_dashboard_banners"
branch_labels = None
depends_on = None


def upgrade():
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("auth_tokens")}
    if "attempt_count" not in columns:
        op.add_column(
            "auth_tokens",
            Column("attempt_count", Integer(), nullable=False, server_default="0"),
        )


def downgrade():
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("auth_tokens")}
    if "attempt_count" in columns:
        op.drop_column("auth_tokens", "attempt_count")
