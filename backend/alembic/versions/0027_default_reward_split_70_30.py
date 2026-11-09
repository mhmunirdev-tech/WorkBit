"""set default verified offer reward split to 70/30
Revision ID: 0027_default_reward_split_70_30
Revises: 0026_fraud_events
"""

from alembic import op
import sqlalchemy as sa


revision = "0027_default_reward_split_70_30"
down_revision = "0026_fraud_events"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        sa.text(
            "UPDATE reward_policies "
            "SET user_reward_percentage = 70.00, "
            "platform_share_percentage = 30.00 "
            "WHERE name = 'default_offer_reward'"
        )
    )


def downgrade():
    op.execute(
        sa.text(
            "UPDATE reward_policies "
            "SET user_reward_percentage = 80.00, "
            "platform_share_percentage = 20.00 "
            "WHERE name = 'default_offer_reward'"
        )
    )
