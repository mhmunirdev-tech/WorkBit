"""track product affiliate attribution and wallet reward settlement"""

from alembic import op
import sqlalchemy as sa


revision = "0033_marketplace_affiliate"
down_revision = "0032_marketplace_mvp"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "marketplace_orders",
        sa.Column("affiliate_referrer_id", sa.String(36), nullable=True),
    )
    op.add_column(
        "marketplace_orders",
        sa.Column("affiliate_rate", sa.Numeric(5, 4), nullable=False, server_default="0.0500"),
    )
    op.add_column(
        "marketplace_orders",
        sa.Column("affiliate_commission_bdt", sa.Numeric(18, 2), nullable=False, server_default="0"),
    )
    op.add_column(
        "marketplace_orders",
        sa.Column("affiliate_reward_amount", sa.Numeric(18, 8), nullable=False, server_default="0"),
    )
    op.add_column(
        "marketplace_orders",
        sa.Column("affiliate_exchange_rate", sa.Numeric(18, 8), nullable=True),
    )
    op.add_column(
        "marketplace_orders",
        sa.Column("affiliate_reward_status", sa.String(24), nullable=False, server_default="NOT_ELIGIBLE"),
    )
    op.create_foreign_key(
        "fk_marketplace_orders_affiliate_referrer",
        "marketplace_orders",
        "users",
        ["affiliate_referrer_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_marketplace_orders_affiliate_referrer_id",
        "marketplace_orders",
        ["affiliate_referrer_id"],
    )


def downgrade():
    op.drop_index("ix_marketplace_orders_affiliate_referrer_id", table_name="marketplace_orders")
    op.drop_constraint("fk_marketplace_orders_affiliate_referrer", "marketplace_orders", type_="foreignkey")
    op.drop_column("marketplace_orders", "affiliate_reward_status")
    op.drop_column("marketplace_orders", "affiliate_exchange_rate")
    op.drop_column("marketplace_orders", "affiliate_reward_amount")
    op.drop_column("marketplace_orders", "affiliate_commission_bdt")
    op.drop_column("marketplace_orders", "affiliate_rate")
    op.drop_column("marketplace_orders", "affiliate_referrer_id")
