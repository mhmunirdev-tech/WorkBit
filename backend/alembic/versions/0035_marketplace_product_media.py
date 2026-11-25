"""Add product gallery images and video media."""

from alembic import op
import sqlalchemy as sa


revision = "0035_product_media"
down_revision = "0034_dynamic_categories"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("marketplace_products", sa.Column("image_url_2", sa.String(1024), nullable=True))
    op.add_column("marketplace_products", sa.Column("image_url_3", sa.String(1024), nullable=True))
    op.add_column("marketplace_products", sa.Column("video_url", sa.String(1024), nullable=True))


def downgrade():
    op.drop_column("marketplace_products", "video_url")
    op.drop_column("marketplace_products", "image_url_3")
    op.drop_column("marketplace_products", "image_url_2")
