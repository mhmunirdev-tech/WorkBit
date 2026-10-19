"""store encrypted user mobile banking payout accounts

Revision ID: 0020_user_payout_accounts
Revises: 0019_default_usd_bdt_rate
"""

import sqlalchemy as sa
from alembic import op

revision = "0020_user_payout_accounts"
down_revision = "0019_default_usd_bdt_rate"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_payout_accounts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("method", sa.String(length=16), nullable=False),
        sa.Column("destination_ciphertext", sa.Text(), nullable=False),
        sa.Column("destination_hint", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "method", name="uq_user_payout_account_method"),
    )
    op.create_index(
        op.f("ix_user_payout_accounts_user_id"),
        "user_payout_accounts",
        ["user_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(op.f("ix_user_payout_accounts_user_id"), table_name="user_payout_accounts")
    op.drop_table("user_payout_accounts")
