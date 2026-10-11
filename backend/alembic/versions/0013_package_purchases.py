"""add manual package purchases
Revision ID: 0013_package_purchases
Revises: 0012_ad_revenue_split
"""

from alembic import op
from app.database.base import Base
import app.models.entities

revision = "0013_package_purchases"
down_revision = "0012_ad_revenue_split"
branch_labels = None
depends_on = None


def upgrade():
    Base.metadata.tables["package_purchases"].create(
        bind=op.get_bind(),
        checkfirst=True,
    )


def downgrade():
    Base.metadata.tables["package_purchases"].drop(
        bind=op.get_bind(),
        checkfirst=True,
    )
