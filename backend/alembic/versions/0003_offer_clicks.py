"""offer click tracking
Revision ID: 0003_offer_clicks
Revises: 0002_offers
"""
from alembic import op
from sqlalchemy import inspect
from app.database.base import Base
import app.models.entities
revision = "0003_offer_clicks"
down_revision = "0002_offers"
branch_labels = None
depends_on = None
def upgrade():
    bind = op.get_bind()
    table = Base.metadata.tables["offer_clicks"]
    if table.name not in inspect(bind).get_table_names():
        table.create(bind=bind)
def downgrade(): Base.metadata.tables["offer_clicks"].drop(bind=op.get_bind())
