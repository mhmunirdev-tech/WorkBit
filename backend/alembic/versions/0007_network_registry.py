"""provider registries for offer and ad monetization
Revision ID: 0007_network_registry
Revises: 0006_withdrawals
"""
from uuid import uuid4

from alembic import op
from sqlalchemy import Boolean, Column, Integer, String, Text, inspect, select

from app.database.base import Base
import app.models.entities

revision = "0007_network_registry"
down_revision = "0006_withdrawals"
branch_labels = None
depends_on = None

OFFER_PROVIDERS = (
    ("Lootably", "lootably", 10),
    ("AdGem", "adgem", 20),
    ("CPAlead", "cpalead", 30),
    ("Offerwall.GG", "offerwall-gg", 40),
    ("Monlix", "monlix", 50),
    ("BitLabs", "bitlabs", 60),
    ("AdGate Media", "adgate", 70),
    ("Torox", "torox", 80),
    ("AdswedMedia", "adswedmedia", 90),
    ("RevU", "revu", 100),
)

AD_NETWORKS = (
    ("WorkBit Ad Manager", "workbit-ad-manager", "AD_MANAGER", 10),
    ("Other Ads", "other-ads", "DISPLAY", 100),
)


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("offer_networks")}
    columns = (
        Column("slug", String(64), nullable=True),
        Column("enabled", Boolean(), nullable=False, server_default="false"),
        Column("api_base_url", String(512), nullable=True),
        Column("api_key_env", String(128), nullable=True),
        Column("publisher_id", String(255), nullable=True),
        Column("placement_id", String(255), nullable=True),
        Column("secret_key_env", String(128), nullable=True),
        Column("postback_url", String(1024), nullable=True),
        Column("integration_type", String(32), nullable=False, server_default="OFFERWALL"),
        Column("country_support", Text(), nullable=False, server_default="[]"),
        Column("device_support", Text(), nullable=False, server_default="[]"),
        Column("priority", Integer(), nullable=False, server_default="100"),
        Column("updated_at", Base.metadata.tables["offer_networks"].c.updated_at.type, nullable=True),
    )
    for column in columns:
        if column.name not in existing_columns:
            op.add_column("offer_networks", column)

    op.execute(
        "UPDATE offer_networks SET slug = lower(replace(provider, '.', '-')) "
        "WHERE slug IS NULL"
    )
    op.execute(
        "UPDATE offer_networks SET updated_at = CURRENT_TIMESTAMP "
        "WHERE updated_at IS NULL"
    )
    with op.batch_alter_table("offer_networks") as batch:
        batch.alter_column("slug", existing_type=String(64), nullable=False)
        batch.alter_column(
            "updated_at",
            existing_type=Base.metadata.tables["offer_networks"].c.updated_at.type,
            nullable=False,
        )
    unique_slug_exists = any(
        set(constraint.get("column_names", [])) == {"slug"}
        for constraint in inspect(bind).get_unique_constraints("offer_networks")
    )
    unique_slug_index_exists = any(
        index["unique"] and index["column_names"] == ["slug"]
        for index in inspect(bind).get_indexes("offer_networks")
    )
    if not unique_slug_exists and not unique_slug_index_exists:
        op.create_index("uq_offer_networks_slug", "offer_networks", ["slug"], unique=True)

    if "ad_networks" not in set(inspect(bind).get_table_names()):
        Base.metadata.tables["ad_networks"].create(bind=bind)
    ad_columns = {column["name"] for column in inspect(bind).get_columns("ad_networks")}
    if "secret_key_env" not in ad_columns:
        op.add_column("ad_networks", Column("secret_key_env", String(128), nullable=True))

    network_table = Base.metadata.tables["offer_networks"]
    existing_slugs = set(bind.execute(select(network_table.c.slug)).scalars())
    for name, slug, priority in OFFER_PROVIDERS:
        if slug not in existing_slugs:
            bind.execute(
                network_table.insert().values(
                    id=str(uuid4()),
                    name=name,
                    provider=slug.upper().replace("-", "_"),
                    slug=slug,
                    enabled=False,
                    integration_type="OFFERWALL",
                    api_key_env=f"{slug.upper().replace('-', '_')}_API_KEY",
                    secret_key_env=f"{slug.upper().replace('-', '_')}_POSTBACK_SECRET",
                    postback_url=f"/api/v1/postbacks/{slug}",
                    country_support="[]",
                    device_support="[]",
                    priority=priority,
                    status="NOT_CONFIGURED",
                )
            )

    ad_table = Base.metadata.tables["ad_networks"]
    existing_ad_slugs = set(bind.execute(select(ad_table.c.slug)).scalars())
    for name, slug, integration_type, priority in AD_NETWORKS:
        if slug not in existing_ad_slugs:
            bind.execute(
                ad_table.insert().values(
                    id=str(uuid4()),
                    name=name,
                    slug=slug,
                    enabled=False,
                    integration_type=integration_type,
                    country_support="[]",
                    device_support="[]",
                    priority=priority,
                    status="NOT_CONFIGURED",
                )
            )


def downgrade():
    bind = op.get_bind()
    if "ad_networks" in set(inspect(bind).get_table_names()):
        if "secret_key_env" in {
            column["name"] for column in inspect(bind).get_columns("ad_networks")
        }:
            op.drop_column("ad_networks", "secret_key_env")
        Base.metadata.tables["ad_networks"].drop(bind=bind)
    if "offer_networks" not in set(inspect(bind).get_table_names()):
        return
    existing_columns = {column["name"] for column in inspect(bind).get_columns("offer_networks")}
    if "slug" in existing_columns:
        network_table = Base.metadata.tables["offer_networks"]
        bind.execute(
            network_table.delete().where(
                network_table.c.slug.in_(
                    [slug for _, slug, _ in OFFER_PROVIDERS]
                )
            )
        )
    with op.batch_alter_table("offer_networks") as batch:
        for index in inspect(bind).get_indexes("offer_networks"):
            if index["name"] == "uq_offer_networks_slug":
                batch.drop_index(index["name"])
        for column_name in (
            "updated_at",
            "priority",
            "device_support",
            "country_support",
            "integration_type",
            "postback_url",
            "secret_key_env",
            "placement_id",
            "publisher_id",
            "api_key_env",
            "api_base_url",
            "enabled",
            "slug",
        ):
            if column_name in existing_columns:
                batch.drop_column(column_name)
