"""add privacy-conscious fraud event records

Revision ID: 0026_fraud_events
Revises: 0025_display_ad_network_slots
"""

import sqlalchemy as sa
from alembic import op


revision = "0026_fraud_events"
down_revision = "0025_display_ad_network_slots"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "fraud_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("evidence_json", sa.Text(), nullable=False),
        sa.Column("ip_hash", sa.String(length=64), nullable=True),
        sa.Column("reviewed_by", sa.String(length=36), nullable=True),
        sa.Column("review_note", sa.String(length=500), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fraud_events_user_id", "fraud_events", ["user_id"])
    op.create_index("ix_fraud_events_event_type", "fraud_events", ["event_type"])
    op.create_index("ix_fraud_events_risk_level", "fraud_events", ["risk_level"])
    op.create_index("ix_fraud_events_status", "fraud_events", ["status"])
    op.create_index("ix_fraud_events_status_created", "fraud_events", ["status", "created_at"])
    op.create_index("ix_fraud_events_risk_created", "fraud_events", ["risk_level", "created_at"])
    op.create_index("ix_fraud_events_ip_created", "fraud_events", ["ip_hash", "created_at"])
    op.create_index("ix_fraud_events_created", "fraud_events", ["created_at"])


def downgrade():
    op.drop_index("ix_fraud_events_created", table_name="fraud_events")
    op.drop_index("ix_fraud_events_ip_created", table_name="fraud_events")
    op.drop_index("ix_fraud_events_risk_created", table_name="fraud_events")
    op.drop_index("ix_fraud_events_status_created", table_name="fraud_events")
    op.drop_index("ix_fraud_events_status", table_name="fraud_events")
    op.drop_index("ix_fraud_events_risk_level", table_name="fraud_events")
    op.drop_index("ix_fraud_events_event_type", table_name="fraud_events")
    op.drop_index("ix_fraud_events_user_id", table_name="fraud_events")
    op.drop_table("fraud_events")
