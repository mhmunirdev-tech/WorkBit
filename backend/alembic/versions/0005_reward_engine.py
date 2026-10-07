"""reward policy and decision tables
Revision ID: 0005_reward_engine
Revises: 0004_conversions
"""
from alembic import op
from sqlalchemy import inspect
from app.database.base import Base
import app.models.entities

revision = "0005_reward_engine"
down_revision = "0004_conversions"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    existing = set(inspect(bind).get_table_names())
    for table_name in ("reward_policies", "reward_decisions"):
        table = Base.metadata.tables.get(table_name)
        if table is not None and table.name not in existing:
            table.create(bind=bind)


def downgrade():
    for table_name in ("reward_decisions", "reward_policies"):
        table = Base.metadata.tables.get(table_name)
        if table is not None:
            table.drop(bind=op.get_bind())
