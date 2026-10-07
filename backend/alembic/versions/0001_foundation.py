"""foundation tables
Revision ID: 0001_foundation
Revises:
"""
from alembic import op
from app.database.base import Base
import app.models.entities
revision = "0001_foundation"
down_revision = None
branch_labels = None
depends_on = None
FOUNDATION_TABLES = (
    "users",
    "profiles",
    "roles",
    "permissions",
    "user_roles",
    "role_permissions",
    "wallets",
    "wallet_transactions",
    "auth_tokens",
    "admin_logs",
)


def upgrade():
    tables = [Base.metadata.tables[name] for name in FOUNDATION_TABLES]
    Base.metadata.create_all(bind=op.get_bind(), tables=tables)


def downgrade():
    tables = [Base.metadata.tables[name] for name in reversed(FOUNDATION_TABLES)]
    Base.metadata.drop_all(bind=op.get_bind(), tables=tables)
