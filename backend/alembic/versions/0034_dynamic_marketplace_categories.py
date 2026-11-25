"""Remove unused starter marketplace categories.

Categories are created by administrators through the marketplace UI. Empty
starter rows from older installations are removed, while categories already
used by products are preserved.
"""

from alembic import op


revision = "0034_dynamic_categories"
down_revision = "0033_marketplace_affiliate"
branch_labels = None
depends_on = None


def upgrade():
    op.get_bind().exec_driver_sql(
        """
        DELETE FROM marketplace_categories
        WHERE slug IN ('digital-products', 'electronics-accessories', 'learning')
          AND NOT EXISTS (
              SELECT 1
              FROM marketplace_products
              WHERE marketplace_products.category_id = marketplace_categories.id
          )
        """
    )


def downgrade():
    # Category data is intentionally administrator-managed and is not restored.
    pass
