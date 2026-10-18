"""configure the initial USD to BDT rate
Revision ID: 0019_default_usd_bdt_rate
Revises: 0018_package_payment_amount
"""

from datetime import datetime, timezone
from decimal import Decimal

import sqlalchemy as sa
from alembic import op

revision = "0019_default_usd_bdt_rate"
down_revision = "0018_package_payment_amount"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    payout_settings = sa.table(
        "payout_settings",
        sa.column("id", sa.String(32)),
        sa.column("usd_bdt_rate", sa.Numeric(18, 8)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    existing = bind.execute(
        sa.select(payout_settings.c.usd_bdt_rate).where(
            payout_settings.c.id == "default"
        )
    ).first()
    if existing is None:
        now = datetime.now(timezone.utc)
        bind.execute(
            sa.insert(payout_settings).values(
                id="default",
                usd_bdt_rate=Decimal("120.0000"),
                updated_at=now,
            )
        )
    elif existing.usd_bdt_rate is None:
        bind.execute(
            sa.update(payout_settings)
            .where(payout_settings.c.id == "default")
            .values(
                usd_bdt_rate=Decimal("120.0000"),
                updated_at=datetime.now(timezone.utc),
            )
        )
