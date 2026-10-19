"""allow up to two payout accounts per mobile banking method"""

import sqlalchemy as sa
from alembic import op

revision = "0021_multiple_payout_accounts"
down_revision = "0020_user_payout_accounts"
branch_labels = None
depends_on = None


def upgrade():
    constraints = sa.inspect(op.get_bind()).get_unique_constraints("user_payout_accounts")
    if any(item.get("name") == "uq_user_payout_account_method" for item in constraints):
        with op.batch_alter_table("user_payout_accounts") as batch_op:
            batch_op.drop_constraint("uq_user_payout_account_method", type_="unique")


def downgrade():
    op.create_unique_constraint(
        "uq_user_payout_account_method",
        "user_payout_accounts",
        ["user_id", "method"],
    )
