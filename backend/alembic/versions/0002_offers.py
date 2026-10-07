"""offer catalog tables
Revision ID: 0002_offers
Revises: 0001_foundation
"""
from alembic import op
from sqlalchemy import inspect
from app.database.base import Base
import app.models.entities
revision = "0002_offers"
down_revision = "0001_foundation"
branch_labels = None
depends_on = None
def upgrade():
    bind = op.get_bind()
    existing = set(inspect(bind).get_table_names())
    for table_name in ("offer_networks", "offers"):
        table = Base.metadata.tables[table_name]
        if table.name not in existing:
            table.create(bind=bind)
def downgrade():
    Base.metadata.tables["offers"].drop(bind=op.get_bind()); Base.metadata.tables["offer_networks"].drop(bind=op.get_bind())
