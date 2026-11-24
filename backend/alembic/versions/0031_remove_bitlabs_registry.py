"""decommission BitLabs offerwall registry entry"""
from uuid import uuid4

from alembic import op
from sqlalchemy import text

revision = "0031_remove_bitlabs_registry"
down_revision = "0030_short_referral_codes"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    bind.execute(
        text(
            """
            UPDATE offer_networks
            SET enabled = false,
                api_key_env = NULL,
                secret_key_env = NULL,
                postback_url = NULL,
                status = 'NOT_CONFIGURED',
                updated_at = CURRENT_TIMESTAMP
            WHERE slug = 'bitlabs'
            """
        )
    )
    bind.execute(
        text(
            """
            DELETE FROM offer_networks
            WHERE slug = 'bitlabs'
              AND NOT EXISTS (
                  SELECT 1 FROM offers
                  WHERE offers.network_id = offer_networks.id
              )
              AND NOT EXISTS (
                  SELECT 1 FROM reward_policies
                  WHERE reward_policies.network_id = offer_networks.id
              )
            """
        )
    )


def downgrade():
    bind = op.get_bind()
    existing = bind.execute(
        text("SELECT id FROM offer_networks WHERE slug = 'bitlabs'")
    ).scalar_one_or_none()
    if existing:
        bind.execute(
            text(
                """
                UPDATE offer_networks
                SET name = 'BitLabs',
                    provider = 'BITLABS',
                    enabled = false,
                    api_key_env = 'BITLABS_API_KEY',
                    secret_key_env = 'BITLABS_POSTBACK_SECRET',
                    postback_url = '/api/v1/postbacks/bitlabs',
                    status = 'NOT_CONFIGURED',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :id
                """
            ),
            {"id": existing},
        )
        return

    bind.execute(
        text(
            """
            INSERT INTO offer_networks (
                id, name, provider, slug, enabled, api_key_env,
                secret_key_env, postback_url, integration_type,
                country_support, device_support, priority, status,
                created_at, updated_at
            ) VALUES (
                :id, 'BitLabs', 'BITLABS', 'bitlabs', false,
                'BITLABS_API_KEY', 'BITLABS_POSTBACK_SECRET',
                '/api/v1/postbacks/bitlabs', 'OFFERWALL',
                '[]', '[]', 60, 'NOT_CONFIGURED',
                CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            """
        ),
        {"id": str(uuid4())},
    )
