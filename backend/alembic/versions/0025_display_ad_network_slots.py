"""add disabled display ad network registry slots

Revision ID: 0025_display_ad_network_slots
Revises: 0024_user_phone_number
"""

from datetime import datetime, timezone
from uuid import uuid4

import sqlalchemy as sa
from alembic import op


revision = "0025_display_ad_network_slots"
down_revision = "0024_user_phone_number"
branch_labels = None
depends_on = None


NETWORKS = (
    ("A-ADS", "a-ads", 20),
    ("Coinzilla", "coinzilla", 30),
    ("Cointraffic", "cointraffic", 40),
    ("PropellerAds", "propellerads", 50),
    ("Monetag", "monetag", 60),
    ("Bitmedia", "bitmedia", 70),
)


def upgrade():
    table = sa.table(
        "ad_networks",
        sa.column("id", sa.String()),
        sa.column("name", sa.String()),
        sa.column("slug", sa.String()),
        sa.column("enabled", sa.Boolean()),
        sa.column("integration_type", sa.String()),
        sa.column("api_key_env", sa.String()),
        sa.column("secret_key_env", sa.String()),
        sa.column("country_support", sa.Text()),
        sa.column("device_support", sa.Text()),
        sa.column("priority", sa.Integer()),
        sa.column("status", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )

    existing = {
        row[0]
        for row in op.get_bind().execute(sa.text("SELECT slug FROM ad_networks"))
    }
    for name, slug, priority in NETWORKS:
        if slug in existing:
            continue
        prefix = slug.upper().replace("-", "_")
        timestamp = datetime.now(timezone.utc)
        op.bulk_insert(
            table,
            [
                {
                    "id": str(uuid4()),
                    "name": name,
                    "slug": slug,
                    "enabled": False,
                    "integration_type": "DISPLAY",
                    "api_key_env": f"{prefix}_API_KEY",
                    "secret_key_env": f"{prefix}_POSTBACK_SECRET",
                    "country_support": "[]",
                    "device_support": "[]",
                    "priority": priority,
                    "status": "NOT_CONFIGURED",
                    "created_at": timestamp,
                    "updated_at": timestamp,
                }
            ],
        )


def downgrade():
    op.execute(
        sa.text(
            "DELETE FROM ad_networks WHERE slug IN "
            "('a-ads', 'coinzilla', 'cointraffic', 'propellerads', 'monetag', 'bitmedia')"
        )
    )
