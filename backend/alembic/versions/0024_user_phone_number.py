"""store user mobile number

Revision ID: 0024_user_phone_number
Revises: 0023_admin_analytics
"""

import sqlalchemy as sa
from alembic import op


revision = "0024_user_phone_number"
down_revision = "0023_admin_analytics"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("phone_number", sa.String(length=16), nullable=True))


def downgrade():
    op.drop_column("users", "phone_number")