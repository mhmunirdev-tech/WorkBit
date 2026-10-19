"""store withdrawal minimum in payout settings

Revision ID: 0022_withdraw_minimum
Revises: 0021_multiple_payout_accounts
"""

from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

from app.core.config import settings

revision = "0022_withdraw_minimum"
down_revision = "0021_multiple_payout_accounts"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "payout_settings",
        sa.Column(
            "minimum_withdrawal_usd",
            sa.Numeric(18, 8),
            nullable=False,
            server_default="5.00",
        ),
    )
    bind = op.get_bind()
    payout_settings = sa.table(
        "payout_settings",
        sa.column("id", sa.String(32)),
        sa.column("usd_bdt_rate", sa.Numeric(18, 8)),
        sa.column("minimum_withdrawal_usd", sa.Numeric(18, 8)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    bind.execute(
        sa.update(payout_settings).values(
            minimum_withdrawal_usd=settings.withdrawal_minimum_amount
        )
    )
    has_default = bind.execute(
        sa.select(payout_settings.c.id).where(payout_settings.c.id == "default")
    ).first()
    if has_default is None:
        bind.execute(
            sa.insert(payout_settings).values(
                id="default",
                usd_bdt_rate=None,
                minimum_withdrawal_usd=settings.withdrawal_minimum_amount,
                updated_at=datetime.now(timezone.utc),
            )
        )


def downgrade():
    op.drop_column("payout_settings", "minimum_withdrawal_usd")
