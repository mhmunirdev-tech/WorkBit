"""create durable reward status notifications

Revision ID: 0028_reward_status_notifications
Revises: 0027_default_reward_split_70_30
"""

import sqlalchemy as sa
from alembic import op


revision = "0028_reward_status_notifications"
down_revision = "0027_default_reward_split_70_30"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "reward_notifications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("reward_decision_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reward_decision_id"], ["reward_decisions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reward_decision_id", "status", name="uq_reward_notification_decision_status"),
    )
    op.create_index("ix_reward_notifications_user_id", "reward_notifications", ["user_id"])
    op.create_index("ix_reward_notifications_reward_decision_id", "reward_notifications", ["reward_decision_id"])
    op.create_index("ix_reward_notifications_user_created", "reward_notifications", ["user_id", "created_at"])


def downgrade():
    op.drop_index("ix_reward_notifications_user_created", table_name="reward_notifications")
    op.drop_index("ix_reward_notifications_reward_decision_id", table_name="reward_notifications")
    op.drop_index("ix_reward_notifications_user_id", table_name="reward_notifications")
    op.drop_table("reward_notifications")
