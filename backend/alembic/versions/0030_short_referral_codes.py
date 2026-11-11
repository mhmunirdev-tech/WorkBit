"""shorten referral codes while retaining existing codes

Revision ID: 0030_short_referral_codes
Revises: 0029_support_tickets
"""

import secrets

import sqlalchemy as sa
from alembic import op


revision = "0030_short_referral_codes"
down_revision = "0029_support_tickets"
branch_labels = None
depends_on = None

_REFERRAL_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _new_code(used_codes: set[str]) -> str:
    for _ in range(100):
        candidate = "WB" + "".join(
            secrets.choice(_REFERRAL_ALPHABET) for _ in range(6)
        )
        if candidate not in used_codes:
            used_codes.add(candidate)
            return candidate
    raise RuntimeError("Unable to generate a unique short referral code.")


def upgrade():
    op.add_column(
        "users",
        sa.Column("legacy_referral_code", sa.String(length=20), nullable=True),
    )
    op.create_index(
        "ix_users_legacy_referral_code",
        "users",
        ["legacy_referral_code"],
        unique=True,
    )

    bind = op.get_bind()
    users = bind.execute(
        sa.text("SELECT id, referral_code FROM users")
    ).mappings().all()
    used_codes = {row["referral_code"].upper() for row in users}

    for user in users:
        old_code = user["referral_code"]
        short_code = _new_code(used_codes)
        bind.execute(
            sa.text(
                "UPDATE users SET referral_code = :short_code, "
                "legacy_referral_code = :old_code WHERE id = :user_id"
            ),
            {
                "short_code": short_code,
                "old_code": old_code,
                "user_id": user["id"],
            },
        )


def downgrade():
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "UPDATE users SET referral_code = legacy_referral_code "
            "WHERE legacy_referral_code IS NOT NULL"
        )
    )
    op.drop_index("ix_users_legacy_referral_code", table_name="users")
    op.drop_column("users", "legacy_referral_code")
