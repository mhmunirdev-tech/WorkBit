"""snapshot package payment amount in BDT
Revision ID: 0018_package_payment_amount
Revises: 0017_withdrawal_payments
"""

import sqlalchemy as sa
from alembic import op

revision = "0018_package_payment_amount"
down_revision = "0017_withdrawal_payments"
branch_labels = None
depends_on = None


def upgrade():
    columns = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("package_purchases")
    }
    if "payment_amount_bdt" not in columns:
        op.add_column(
            "package_purchases",
            sa.Column("payment_amount_bdt", sa.Numeric(18, 2), nullable=True),
        )
    if "usd_bdt_rate" not in columns:
        op.add_column(
            "package_purchases",
            sa.Column("usd_bdt_rate", sa.Numeric(18, 8), nullable=True),
        )


def downgrade():
    columns = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("package_purchases")
    }
    if "usd_bdt_rate" in columns:
        op.drop_column("package_purchases", "usd_bdt_rate")
    if "payment_amount_bdt" in columns:
        op.drop_column("package_purchases", "payment_amount_bdt")
