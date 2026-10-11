"""add BDT mobile-banking payout exchange snapshots
Revision ID: 0014_mobile_payout_settings
Revises: 0013_package_purchases
"""

import sqlalchemy as sa
from alembic import op
from app.database.base import Base
import app.models.entities

revision = "0014_mobile_payout_settings"
down_revision = "0013_package_purchases"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("withdrawal_requests")}
    for column in (
        sa.Column("payout_amount", sa.Numeric(18, 8), nullable=True),
        sa.Column("payout_currency", sa.String(3), nullable=True),
        sa.Column("exchange_rate", sa.Numeric(18, 8), nullable=True),
    ):
        if column.name not in columns:
            op.add_column("withdrawal_requests", column)
    Base.metadata.tables["payout_settings"].create(bind=bind, checkfirst=True)


def downgrade():
    Base.metadata.tables["payout_settings"].drop(bind=op.get_bind(), checkfirst=True)
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("withdrawal_requests")}
    for name in ("exchange_rate", "payout_currency", "payout_amount"):
        if name in columns:
            op.drop_column("withdrawal_requests", name)
