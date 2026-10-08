"""create dashboard banners for the admin CMS
Revision ID: 0009_dashboard_banners
Revises: 0008_profile_avatar
"""

from alembic import op

from app.database.base import Base
import app.models.entities

revision = "0009_dashboard_banners"
down_revision = "0008_profile_avatar"
branch_labels = None
depends_on = None


def upgrade():
    Base.metadata.tables["dashboard_banners"].create(bind=op.get_bind(), checkfirst=True)


def downgrade():
    Base.metadata.tables["dashboard_banners"].drop(bind=op.get_bind(), checkfirst=True)
