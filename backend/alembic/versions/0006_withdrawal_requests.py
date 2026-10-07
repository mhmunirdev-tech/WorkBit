"""manual withdrawal requests and review
Revision ID: 0006_withdrawals
Revises: 0005_reward_engine
"""
from alembic import op
from sqlalchemy import inspect

from app.database.base import Base
import app.models.entities

revision = "0006_withdrawals"
down_revision = "0005_reward_engine"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if "withdrawal_requests" not in set(inspect(bind).get_table_names()):
        Base.metadata.tables["withdrawal_requests"].create(bind=bind)


def downgrade():
    Base.metadata.tables["withdrawal_requests"].drop(bind=op.get_bind())
