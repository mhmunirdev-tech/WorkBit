"""normalized conversion records
Revision ID: 0004_conversions
Revises: 0003_offer_clicks
"""
from alembic import op
from sqlalchemy import inspect
from app.database.base import Base
import app.models.entities
revision = "0004_conversions"
down_revision = "0003_offer_clicks"
branch_labels = None
depends_on = None
def upgrade():
    bind = op.get_bind()
    table = Base.metadata.tables["offer_conversions"]
    if table.name not in inspect(bind).get_table_names():
        table.create(bind=bind)
def downgrade(): Base.metadata.tables["offer_conversions"].drop(bind=op.get_bind())
