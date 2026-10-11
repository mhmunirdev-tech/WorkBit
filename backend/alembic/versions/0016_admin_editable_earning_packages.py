"""make earning packages database-managed and editable

Revision ID: 0016_editable_earning_packages
Revises: 0015_deposits_package_terms
"""

from decimal import Decimal

import sqlalchemy as sa
from alembic import op

revision = "0016_editable_earning_packages"
down_revision = "0015_deposits_package_terms"
branch_labels = None
depends_on = None


PACKAGES = (
    ("BASIC", "Basic", "For test update to feature", Decimal("10.00"), 365, 10),
    ("STANDARD", "Standard", "For test", Decimal("50.00"), 730, 20),
    ("PREMIUM", "Premium", "For test", Decimal("100.00"), 1095, 30),
    ("VIP", "VIP", "Package Duration", Decimal("550.00"), 1095, 40),
    ("VIP_PRO", "VIP Pro", "Details", Decimal("1000.00"), 1825, 50),
    ("FOUNDER", "Founder", "Package Duration", Decimal("500.00"), 3650, 60),
)


def upgrade():
    op.create_table(
        "earning_packages",
        sa.Column("code", sa.String(length=32), primary_key=True),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
    )
    op.create_index(
        "ix_earning_packages_is_active",
        "earning_packages",
        ["is_active"],
    )

    bind = op.get_bind()
    packages = sa.table(
        "earning_packages",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("amount", sa.Numeric(18, 2)),
        sa.column("currency", sa.String),
        sa.column("duration_days", sa.Integer),
        sa.column("is_active", sa.Boolean),
        sa.column("sort_order", sa.Integer),
    )
    bind.execute(
        packages.insert(),
        [
            {
                "code": code,
                "name": name,
                "description": description,
                "amount": amount,
                "currency": "USD",
                "duration_days": duration_days,
                "is_active": True,
                "sort_order": sort_order,
            }
            for code, name, description, amount, duration_days, sort_order in PACKAGES
        ],
    )

    purchase_columns = {
        column["name"]
        for column in sa.inspect(bind).get_columns("package_purchases")
    }
    if "duration_days" not in purchase_columns:
        op.add_column(
            "package_purchases",
            sa.Column("duration_days", sa.Integer(), nullable=False, server_default="30"),
        )
        op.execute(
            sa.text(
                "UPDATE package_purchases SET duration_days = 60 "
                "WHERE package_code = 'PRO'"
            )
        )


def downgrade():
    bind = op.get_bind()
    purchase_columns = {
        column["name"]
        for column in sa.inspect(bind).get_columns("package_purchases")
    }
    if "duration_days" in purchase_columns:
        op.drop_column("package_purchases", "duration_days")
    op.drop_index("ix_earning_packages_is_active", table_name="earning_packages")
    op.drop_table("earning_packages")
