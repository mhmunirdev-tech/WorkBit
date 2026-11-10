"""add user support tickets

Revision ID: 0029_support_tickets
Revises: 0028_reward_status_notifications
"""

import sqlalchemy as sa
from alembic import op
from uuid import uuid4


revision = "0029_support_tickets"
down_revision = "0028_reward_status_notifications"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    permission_id = str(uuid4())
    bind.execute(
        sa.text("INSERT INTO permissions (id, name) VALUES (:id, :name)"),
        {"id": permission_id, "name": "support.manage"},
    )
    bind.execute(
        sa.text(
            "INSERT INTO role_permissions (role_id, permission_id) "
            "SELECT roles.id, :permission_id FROM roles "
            "WHERE roles.name IN ('ADMIN', 'SUPER_ADMIN')"
        ),
        {"permission_id": permission_id},
    )
    op.create_table(
        "support_tickets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("subject", sa.String(length=120), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="OPEN"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_support_tickets_user_id", "support_tickets", ["user_id"])
    op.create_index("ix_support_tickets_status", "support_tickets", ["status"])
    op.create_index(
        "ix_support_tickets_user_updated", "support_tickets", ["user_id", "updated_at"]
    )
    op.create_table(
        "support_ticket_messages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("ticket_id", sa.String(length=36), nullable=False),
        sa.Column("sender_user_id", sa.String(length=36), nullable=False),
        sa.Column("sender_role", sa.String(length=16), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["ticket_id"], ["support_tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_support_ticket_messages_ticket_id", "support_ticket_messages", ["ticket_id"]
    )
    op.create_index(
        "ix_support_ticket_messages_sender_user_id",
        "support_ticket_messages",
        ["sender_user_id"],
    )


def downgrade():
    op.drop_index(
        "ix_support_ticket_messages_sender_user_id", table_name="support_ticket_messages"
    )
    op.drop_index(
        "ix_support_ticket_messages_ticket_id", table_name="support_ticket_messages"
    )
    op.drop_table("support_ticket_messages")
    op.drop_index("ix_support_tickets_user_updated", table_name="support_tickets")
    op.drop_index("ix_support_tickets_status", table_name="support_tickets")
    op.drop_index("ix_support_tickets_user_id", table_name="support_tickets")
    op.drop_table("support_tickets")
    bind = op.get_bind()
    permission_id = bind.scalar(
        sa.text("SELECT id FROM permissions WHERE name = :name"),
        {"name": "support.manage"},
    )
    if permission_id is not None:
        bind.execute(
            sa.text("DELETE FROM role_permissions WHERE permission_id = :permission_id"),
            {"permission_id": permission_id},
        )
        bind.execute(
            sa.text("DELETE FROM permissions WHERE id = :permission_id"),
            {"permission_id": permission_id},
        )
