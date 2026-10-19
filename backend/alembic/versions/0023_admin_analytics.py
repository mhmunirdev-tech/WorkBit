"""store anonymized visitor and failed login analytics

Revision ID: 0023_admin_analytics
Revises: 0022_withdraw_minimum
"""

import sqlalchemy as sa
from alembic import op

revision = "0023_admin_analytics"
down_revision = "0022_withdraw_minimum"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "analytics_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("visitor_hash", sa.String(length=64), nullable=True),
        sa.Column("path", sa.String(length=256), nullable=True),
        sa.Column("login_type", sa.String(length=16), nullable=True),
        sa.Column("email_masked", sa.String(length=320), nullable=True),
        sa.Column("ip_hash", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_analytics_events_type_created",
        "analytics_events",
        ["event_type", "created_at"],
    )
    op.create_index(
        "ix_analytics_events_visitor_created",
        "analytics_events",
        ["visitor_hash", "created_at"],
    )
    op.create_index(
        "ix_analytics_events_created",
        "analytics_events",
        ["created_at"],
    )


def downgrade():
    op.drop_index("ix_analytics_events_created", table_name="analytics_events")
    op.drop_index("ix_analytics_events_visitor_created", table_name="analytics_events")
    op.drop_index("ix_analytics_events_type_created", table_name="analytics_events")
    op.drop_table("analytics_events")
