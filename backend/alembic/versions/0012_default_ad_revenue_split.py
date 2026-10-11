"""set the default ad reward split to 80/20
Revision ID: 0012_ad_revenue_split
Revises: 0011_terms_rank_tiers
"""

from alembic import op
import sqlalchemy as sa

revision = "0012_ad_revenue_split"
down_revision = "0011_terms_rank_tiers"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        sa.text(
            "UPDATE reward_policies "
            "SET user_reward_percentage = 80.00, "
            "platform_share_percentage = 20.00, "
            "minimum_reward = 0.00, "
            "maximum_reward = 0.00 "
            "WHERE name = 'default_offer_reward'"
        )
    )


def downgrade():
    op.execute(
        sa.text(
            "UPDATE reward_policies "
            "SET user_reward_percentage = 70.00, "
            "platform_share_percentage = 30.00, "
            "minimum_reward = 0.10, "
            "maximum_reward = 25.00 "
            "WHERE name = 'default_offer_reward'"
        )
    )
