"""record payout transaction references and paid timestamps
Revision ID: 0017_withdrawal_payment_reference
Revises: 0016_editable_earning_packages
"""

import sqlalchemy as sa
from alembic import op

revision = "0017_withdrawal_payments"
down_revision = "0016_editable_earning_packages"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    columns = {
        column["name"]
        for column in sa.inspect(bind).get_columns("withdrawal_requests")
    }
    if "payment_transaction_id" not in columns:
        op.add_column(
            "withdrawal_requests",
            sa.Column("payment_transaction_id", sa.String(128), nullable=True),
        )
    if "paid_at" not in columns:
        op.add_column(
            "withdrawal_requests",
            sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        )

    indexes = {
        index["name"]
        for index in sa.inspect(bind).get_indexes("withdrawal_requests")
    }
    constraints = {
        constraint["name"]
        for constraint in sa.inspect(bind).get_unique_constraints(
            "withdrawal_requests"
        )
    }
    if (
        "uq_withdrawal_method_payment_transaction" not in indexes
        and "uq_withdrawal_method_payment_transaction" not in constraints
    ):
        op.create_index(
            "uq_withdrawal_method_payment_transaction",
            "withdrawal_requests",
            ["method", "payment_transaction_id"],
            unique=True,
        )

    op.execute(
        sa.text(
            "UPDATE withdrawal_requests SET status = 'PAID' "
            "WHERE status = 'COMPLETED'"
        )
    )


def downgrade():
    bind = op.get_bind()
    op.execute(
        sa.text(
            "UPDATE withdrawal_requests SET status = 'COMPLETED' "
            "WHERE status = 'PAID'"
        )
    )
    indexes = {
        index["name"]
        for index in sa.inspect(bind).get_indexes("withdrawal_requests")
    }
    if "uq_withdrawal_method_payment_transaction" in indexes:
        op.drop_index(
            "uq_withdrawal_method_payment_transaction",
            table_name="withdrawal_requests",
        )
    constraints = {
        constraint["name"]
        for constraint in sa.inspect(bind).get_unique_constraints(
            "withdrawal_requests"
        )
    }
    if "uq_withdrawal_method_payment_transaction" in constraints:
        if bind.dialect.name == "sqlite":
            with op.batch_alter_table("withdrawal_requests") as batch_op:
                batch_op.drop_constraint(
                    "uq_withdrawal_method_payment_transaction",
                    type_="unique",
                )
        else:
            op.drop_constraint(
                "uq_withdrawal_method_payment_transaction",
                "withdrawal_requests",
                type_="unique",
            )
    columns = {
        column["name"]
        for column in sa.inspect(bind).get_columns("withdrawal_requests")
    }
    if "paid_at" in columns:
        op.drop_column("withdrawal_requests", "paid_at")
    if "payment_transaction_id" in columns:
        op.drop_column("withdrawal_requests", "payment_transaction_id")
