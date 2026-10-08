"""store user profile avatar URLs
Revision ID: 0008_profile_avatar
Revises: 0007_network_registry
"""

from alembic import op
from sqlalchemy import Column, String, inspect

revision = "0008_profile_avatar"
down_revision = "0007_network_registry"
branch_labels = None
depends_on = None


def upgrade():
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("profiles")}
    if "avatar_url" not in columns:
        op.add_column("profiles", Column("avatar_url", String(1024), nullable=True))


def downgrade():
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("profiles")}
    if "avatar_url" in columns:
        op.drop_column("profiles", "avatar_url")
