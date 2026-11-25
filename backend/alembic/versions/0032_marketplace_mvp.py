"""add the first-party marketplace catalog, cart, and orders"""

from alembic import op
import sqlalchemy as sa


revision = "0032_marketplace_mvp"
down_revision = "0031_remove_bitlabs_registry"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "marketplace_categories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(80), nullable=False, unique=True),
        sa.Column("slug", sa.String(96), nullable=False, unique=True),
        sa.Column("description", sa.String(500), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_marketplace_categories_slug", "marketplace_categories", ["slug"], unique=True)
    op.create_index("ix_marketplace_categories_is_active", "marketplace_categories", ["is_active"])

    op.create_table(
        "marketplace_products",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("category_id", sa.String(36), sa.ForeignKey("marketplace_categories.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("sku", sa.String(64), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("slug", sa.String(180), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("image_url", sa.String(1024), nullable=True),
        sa.Column("price", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="BDT"),
        sa.Column("stock_quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("featured", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("category_id", "sku", name="uq_marketplace_product_category_sku"),
    )
    op.create_index("ix_marketplace_products_category_id", "marketplace_products", ["category_id"])
    op.create_index("ix_marketplace_products_sku", "marketplace_products", ["sku"])
    op.create_index("ix_marketplace_products_slug", "marketplace_products", ["slug"], unique=True)
    op.create_index("ix_marketplace_products_is_active", "marketplace_products", ["is_active"])
    op.create_index("ix_marketplace_products_featured", "marketplace_products", ["featured"])

    op.create_table(
        "marketplace_carts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_marketplace_carts_user_id", "marketplace_carts", ["user_id"], unique=True)

    op.create_table(
        "marketplace_cart_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("cart_id", sa.String(36), sa.ForeignKey("marketplace_carts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("marketplace_products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("cart_id", "product_id", name="uq_marketplace_cart_product"),
    )
    op.create_index("ix_marketplace_cart_items_cart_id", "marketplace_cart_items", ["cart_id"])
    op.create_index("ix_marketplace_cart_items_product_id", "marketplace_cart_items", ["product_id"])

    op.create_table(
        "marketplace_orders",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column("payment_method", sa.String(32), nullable=False, server_default="COD"),
        sa.Column("payment_reference", sa.String(120), nullable=True),
        sa.Column("subtotal", sa.Numeric(18, 2), nullable=False),
        sa.Column("delivery_fee", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("total", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="BDT"),
        sa.Column("shipping_name", sa.String(120), nullable=False),
        sa.Column("shipping_phone", sa.String(32), nullable=False),
        sa.Column("shipping_address", sa.String(500), nullable=False),
        sa.Column("shipping_city", sa.String(80), nullable=False),
        sa.Column("customer_note", sa.String(500), nullable=False, server_default=""),
        sa.Column("admin_note", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_marketplace_orders_user_id", "marketplace_orders", ["user_id"])
    op.create_index("ix_marketplace_orders_status", "marketplace_orders", ["status"])

    op.create_table(
        "marketplace_order_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("order_id", sa.String(36), sa.ForeignKey("marketplace_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.String(36), nullable=False),
        sa.Column("product_name", sa.String(160), nullable=False),
        sa.Column("sku", sa.String(64), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 2), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("line_total", sa.Numeric(18, 2), nullable=False),
    )
    op.create_index("ix_marketplace_order_items_order_id", "marketplace_order_items", ["order_id"])
    op.create_index("ix_marketplace_order_items_product_id", "marketplace_order_items", ["product_id"])

    bind = op.get_bind()
    permission_id = str(uuid4())
    bind.execute(
        sa.text(
            "INSERT INTO permissions (id, name) VALUES (:id, 'marketplace.manage') "
            "ON CONFLICT (name) DO NOTHING"
        ),
        {"id": permission_id},
    )
    bind.execute(
        sa.text(
            "INSERT INTO role_permissions (role_id, permission_id) "
            "SELECT roles.id, permissions.id FROM roles, permissions "
            "WHERE roles.name IN ('ADMIN', 'SUPER_ADMIN') AND permissions.name = 'marketplace.manage' "
            "ON CONFLICT DO NOTHING"
        )
    )

def downgrade():
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE permission_id IN "
            "(SELECT id FROM permissions WHERE name = 'marketplace.manage')"
        )
    )
    bind.execute(sa.text("DELETE FROM permissions WHERE name = 'marketplace.manage'"))
    op.drop_index("ix_marketplace_order_items_product_id", table_name="marketplace_order_items")
    op.drop_index("ix_marketplace_order_items_order_id", table_name="marketplace_order_items")
    op.drop_table("marketplace_order_items")
    op.drop_index("ix_marketplace_orders_status", table_name="marketplace_orders")
    op.drop_index("ix_marketplace_orders_user_id", table_name="marketplace_orders")
    op.drop_table("marketplace_orders")
    op.drop_index("ix_marketplace_cart_items_product_id", table_name="marketplace_cart_items")
    op.drop_index("ix_marketplace_cart_items_cart_id", table_name="marketplace_cart_items")
    op.drop_table("marketplace_cart_items")
    op.drop_index("ix_marketplace_carts_user_id", table_name="marketplace_carts")
    op.drop_table("marketplace_carts")
    op.drop_index("ix_marketplace_products_featured", table_name="marketplace_products")
    op.drop_index("ix_marketplace_products_is_active", table_name="marketplace_products")
    op.drop_index("ix_marketplace_products_slug", table_name="marketplace_products")
    op.drop_index("ix_marketplace_products_sku", table_name="marketplace_products")
    op.drop_index("ix_marketplace_products_category_id", table_name="marketplace_products")
    op.drop_table("marketplace_products")
    op.drop_index("ix_marketplace_categories_is_active", table_name="marketplace_categories")
    op.drop_index("ix_marketplace_categories_slug", table_name="marketplace_categories")
    op.drop_table("marketplace_categories")
