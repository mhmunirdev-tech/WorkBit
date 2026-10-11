"""add reviewed wallet deposits and package terms
Revision ID: 0015_deposits_package_terms
Revises: 0014_mobile_payout_settings
"""

import sqlalchemy as sa
from alembic import op
from app.database.base import Base
import app.models.entities
from calendar import monthrange

revision = "0015_deposits_package_terms"
down_revision = "0014_mobile_payout_settings"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()

    wallet_columns = {column["name"] for column in sa.inspect(bind).get_columns("wallets")}
    if "deposit_balance" not in wallet_columns:
        op.add_column(
            "wallets",
            sa.Column(
                "deposit_balance",
                sa.Numeric(18, 8),
                nullable=False,
                server_default="0",
            ),
        )

    purchase_columns = {
        column["name"] for column in sa.inspect(bind).get_columns("package_purchases")
    }
    for column in (
        sa.Column("deposit_amount", sa.Numeric(18, 8), nullable=False, server_default="0"),
        sa.Column("earning_amount", sa.Numeric(18, 8), nullable=False, server_default="0"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    ):
        if column.name not in purchase_columns:
            op.add_column("package_purchases", column)

    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text(
                """
                UPDATE package_purchases
                SET starts_at = COALESCE(reviewed_at, created_at),
                    expires_at = COALESCE(reviewed_at, created_at) +
                        CASE WHEN package_code = 'PRO'
                             THEN INTERVAL '2 months'
                             ELSE INTERVAL '1 month'
                        END
                WHERE status = 'APPROVED' AND expires_at IS NULL
                """
            )
        )
    else:
        purchases = sa.table(
            "package_purchases",
            sa.column("id", sa.String),
            sa.column("package_code", sa.String),
            sa.column("created_at", sa.DateTime(timezone=True)),
            sa.column("reviewed_at", sa.DateTime(timezone=True)),
            sa.column("starts_at", sa.DateTime(timezone=True)),
            sa.column("expires_at", sa.DateTime(timezone=True)),
            sa.column("status", sa.String),
        )
        rows = bind.execute(
            sa.select(
                purchases.c.id,
                purchases.c.package_code,
                purchases.c.created_at,
                purchases.c.reviewed_at,
            ).where(purchases.c.status == "APPROVED", purchases.c.expires_at.is_(None))
        )
        for purchase_id, code, created_at, reviewed_at in rows:
            start = reviewed_at or created_at
            months = 2 if code == "PRO" else 1
            month_index = start.month - 1 + months
            year = start.year + month_index // 12
            month = month_index % 12 + 1
            expiry = start.replace(year=year, month=month, day=min(start.day, monthrange(year, month)[1]))
            bind.execute(
                purchases.update()
                .where(purchases.c.id == purchase_id)
                .values(starts_at=start, expires_at=expiry)
            )
    Base.metadata.tables["deposit_requests"].create(bind=bind, checkfirst=True)
    Base.metadata.tables["payment_references"].create(bind=bind, checkfirst=True)
    payment_references = Base.metadata.tables["payment_references"]
    package_purchases = Base.metadata.tables["package_purchases"]
    for payment_method, payment_reference, request_id, created_at in bind.execute(
        sa.select(
            package_purchases.c.payment_method,
            package_purchases.c.payment_reference,
            package_purchases.c.id,
            package_purchases.c.created_at,
        )
    ):
        bind.execute(
            payment_references.insert().values(
                payment_method=payment_method,
                payment_reference=payment_reference,
                request_type="PACKAGE",
                request_id=request_id,
                created_at=created_at,
            )
        )


def downgrade():
    bind = op.get_bind()
    Base.metadata.tables["deposit_requests"].drop(bind=bind, checkfirst=True)
    Base.metadata.tables["payment_references"].drop(bind=bind, checkfirst=True)
    for table, names in (
        ("package_purchases", ("expires_at", "starts_at", "earning_amount", "deposit_amount")),
        ("wallets", ("deposit_balance",)),
    ):
        columns = {column["name"] for column in sa.inspect(bind).get_columns(table)}
        for name in names:
            if name in columns:
                op.drop_column(table, name)
