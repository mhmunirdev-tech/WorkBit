import uuid
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from urllib.parse import quote
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.api.deps import current_user, require_permission
from app.database.session import get_db
from app.core.config import settings
from app.integrations.cloudinary import upload_image, upload_video
from app.models import (
    MarketplaceCartItem,
    MarketplaceCategory,
    MarketplaceOrder,
    MarketplaceProduct,
    User,
)
from app.schemas.marketplace import (
    MarketplaceCartItemAdd,
    MarketplaceCartItemRead,
    MarketplaceCartItemUpdate,
    MarketplaceCartRead,
    MarketplaceCategoryCreate,
    MarketplaceCategoryRead,
    MarketplaceOrderCreate,
    MarketplaceOrderRead,
    MarketplaceOrderStatusUpdate,
    MarketplaceProductCreate,
    MarketplaceProductRead,
)
from app.services.marketplace import (
    cart_read,
    category_read,
    create_order,
    get_or_create_cart,
    order_read,
    product_read,
    update_order_status,
)

router = APIRouter(tags=["marketplace"])
marketplace_admin = require_permission("marketplace.manage")
MAX_PRODUCT_IMAGE_SIZE = 5 * 1024 * 1024
MAX_PRODUCT_VIDEO_SIZE = 50 * 1024 * 1024
PRODUCT_IMAGE_SIGNATURES = {
    "image/jpeg": lambda data: data.startswith(b"\xff\xd8\xff"),
    "image/png": lambda data: data.startswith(b"\x89PNG\r\n\x1a\n"),
    "image/webp": lambda data: data.startswith(b"RIFF") and data[8:12] == b"WEBP",
}
PRODUCT_VIDEO_TYPES = {"video/mp4", "video/webm", "video/quicktime"}


def _valid_product_video(data: bytes, content_type: str) -> bool:
    if content_type == "video/webm":
        return data.startswith(b"\x1a\x45\xdf\xa3")
    return len(data) >= 12 and data[4:8] == b"ftyp"


@router.get("/marketplace/referral-link")
def marketplace_referral_link(
    product: str | None = Query(default=None, max_length=180),
    user: User = Depends(current_user),
) -> dict[str, str]:
    url = f"{settings.frontend_origin.rstrip('/')}/marketplace?ref={quote(user.referral_code)}"
    if product and product.strip():
        url += f"&product={quote(product.strip())}"
    return {"referral_code": user.referral_code, "url": url}


def _category_counts(db: Session, categories: list[MarketplaceCategory]) -> dict[str, int]:
    if not categories:
        return {}
    rows = db.execute(
        select(MarketplaceProduct.category_id, func.count(MarketplaceProduct.id))
        .where(MarketplaceProduct.category_id.in_([item.id for item in categories]))
        .group_by(MarketplaceProduct.category_id)
    ).all()
    return {category_id: count for category_id, count in rows}


def _active_product_query():
    return (
        select(MarketplaceProduct)
        .join(MarketplaceCategory)
        .where(
            MarketplaceProduct.is_active.is_(True),
            MarketplaceCategory.is_active.is_(True),
        )
        .options(joinedload(MarketplaceProduct.category))
    )


@router.get("/marketplace/categories", response_model=list[MarketplaceCategoryRead])
def public_categories(db: Session = Depends(get_db)) -> list[dict]:
    categories = list(
        db.scalars(
            select(MarketplaceCategory)
            .where(MarketplaceCategory.is_active.is_(True))
            .order_by(MarketplaceCategory.sort_order, MarketplaceCategory.name)
        ).all()
    )
    counts = _category_counts(db, categories)
    return [category_read(category, counts.get(category.id, 0)) for category in categories]


@router.get("/marketplace/products", response_model=list[MarketplaceProductRead])
def public_products(
    category: str | None = Query(default=None, max_length=96),
    search: str | None = Query(default=None, max_length=100),
    featured: bool | None = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    query = _active_product_query()
    if category:
        query = query.where(MarketplaceCategory.slug == category.strip().lower())
    if search and search.strip():
        query = query.where(MarketplaceProduct.name.ilike(f"%{search.strip()}%"))
    if featured is not None:
        query = query.where(MarketplaceProduct.featured.is_(featured))
    products = db.scalars(
        query.order_by(MarketplaceProduct.sort_order, MarketplaceProduct.created_at.desc()).limit(100)
    ).all()
    return [product_read(product) for product in products]


@router.get("/marketplace/products/{slug}", response_model=MarketplaceProductRead)
def public_product(slug: str, db: Session = Depends(get_db)) -> dict:
    product = db.scalar(_active_product_query().where(MarketplaceProduct.slug == slug))
    if product is None:
        raise HTTPException(404, "Product not found.")
    return product_read(product)


@router.get("/marketplace/cart", response_model=MarketplaceCartRead)
def get_cart(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    return cart_read(get_or_create_cart(db, user))


@router.post("/marketplace/cart/items", response_model=MarketplaceCartRead, status_code=status.HTTP_201_CREATED)
def add_cart_item(
    data: MarketplaceCartItemAdd,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    product = db.scalar(
        _active_product_query().where(MarketplaceProduct.id == data.product_id)
    )
    if product is None:
        raise HTTPException(404, "Product not found.")
    cart = get_or_create_cart(db, user)
    item = next((entry for entry in cart.items if entry.product_id == product.id), None)
    next_quantity = data.quantity + (item.quantity if item else 0)
    if next_quantity > product.stock_quantity:
        raise HTTPException(409, "The requested quantity is not available in stock.")
    if item:
        item.quantity = next_quantity
    else:
        cart.items.append(MarketplaceCartItem(product_id=product.id, quantity=data.quantity, product=product))
    db.commit()
    return cart_read(get_or_create_cart(db, user))


@router.patch("/marketplace/cart/items/{item_id}", response_model=MarketplaceCartRead)
def update_cart_item(
    item_id: str,
    data: MarketplaceCartItemUpdate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    item = db.scalar(
        select(MarketplaceCartItem)
        .join(MarketplaceCartItem.cart)
        .where(MarketplaceCartItem.id == item_id, MarketplaceCartItem.cart.has(user_id=user.id))
        .options(joinedload(MarketplaceCartItem.product))
    )
    if item is None:
        raise HTTPException(404, "Cart item not found.")
    if data.quantity > item.product.stock_quantity:
        raise HTTPException(409, "The requested quantity is not available in stock.")
    item.quantity = data.quantity
    db.commit()
    return cart_read(get_or_create_cart(db, user))


@router.delete("/marketplace/cart/items/{item_id}", response_model=MarketplaceCartRead)
def delete_cart_item(
    item_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    item = db.scalar(
        select(MarketplaceCartItem)
        .join(MarketplaceCartItem.cart)
        .where(MarketplaceCartItem.id == item_id, MarketplaceCartItem.cart.has(user_id=user.id))
    )
    if item is None:
        raise HTTPException(404, "Cart item not found.")
    db.delete(item)
    db.commit()
    return cart_read(get_or_create_cart(db, user))


@router.post("/marketplace/orders", response_model=MarketplaceOrderRead, status_code=status.HTTP_201_CREATED)
def submit_order(
    data: MarketplaceOrderCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    return order_read(create_order(db, user, data))


@router.get("/marketplace/orders", response_model=list[MarketplaceOrderRead])
def user_orders(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[dict]:
    orders = db.scalars(
        select(MarketplaceOrder)
        .where(MarketplaceOrder.user_id == user.id)
        .options(selectinload(MarketplaceOrder.items), joinedload(MarketplaceOrder.user))
        .order_by(MarketplaceOrder.created_at.desc())
    ).all()
    return [order_read(order) for order in orders]


@router.get("/marketplace/orders/{order_id}", response_model=MarketplaceOrderRead)
def user_order(order_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    order = db.scalar(
        select(MarketplaceOrder)
        .where(MarketplaceOrder.id == order_id, MarketplaceOrder.user_id == user.id)
        .options(selectinload(MarketplaceOrder.items), joinedload(MarketplaceOrder.user))
    )
    if order is None:
        raise HTTPException(404, "Order not found.")
    return order_read(order)


@router.get("/admin/marketplace/categories", response_model=list[MarketplaceCategoryRead])
def admin_categories(_: User = Depends(marketplace_admin), db: Session = Depends(get_db)) -> list[dict]:
    categories = list(
        db.scalars(select(MarketplaceCategory).order_by(MarketplaceCategory.sort_order, MarketplaceCategory.name)).all()
    )
    counts = _category_counts(db, categories)
    return [category_read(category, counts.get(category.id, 0)) for category in categories]


@router.post("/admin/marketplace/products/upload-image")
def upload_product_image(
    file: UploadFile = File(...),
    _: User = Depends(marketplace_admin),
) -> dict[str, str]:
    content_type = file.content_type or ""
    signature_check = PRODUCT_IMAGE_SIGNATURES.get(content_type)
    if signature_check is None:
        raise HTTPException(415, "Choose a JPEG, PNG, or WebP product image.")
    image = file.file.read(MAX_PRODUCT_IMAGE_SIZE + 1)
    if len(image) > MAX_PRODUCT_IMAGE_SIZE:
        raise HTTPException(413, "Product images must be 5 MB or smaller.")
    if not signature_check(image):
        raise HTTPException(415, "The uploaded file is not a valid supported image.")
    return {
        "media_url": upload_image(
            image,
            content_type,
            f"workbit/products/{uuid.uuid4()}",
        )
    }


@router.post("/admin/marketplace/products/upload-video")
def upload_product_video(
    file: UploadFile = File(...),
    _: User = Depends(marketplace_admin),
) -> dict[str, str]:
    content_type = file.content_type or ""
    if content_type not in PRODUCT_VIDEO_TYPES:
        raise HTTPException(415, "Choose an MP4, WebM, or MOV product video.")
    video = file.file.read(MAX_PRODUCT_VIDEO_SIZE + 1)
    if len(video) > MAX_PRODUCT_VIDEO_SIZE:
        raise HTTPException(413, "Product videos must be 50 MB or smaller.")
    if not _valid_product_video(video, content_type):
        raise HTTPException(415, "The uploaded file is not a valid supported video.")
    return {
        "media_url": upload_video(
            video,
            content_type,
            f"workbit/products/{uuid.uuid4()}",
        )
    }


@router.post("/admin/marketplace/categories", response_model=MarketplaceCategoryRead, status_code=201)
def create_category(
    data: MarketplaceCategoryCreate,
    _: User = Depends(marketplace_admin),
    db: Session = Depends(get_db),
) -> dict:
    if db.scalar(select(MarketplaceCategory).where((MarketplaceCategory.slug == data.slug) | (MarketplaceCategory.name == data.name))):
        raise HTTPException(409, "A category with this name or slug already exists.")
    category = MarketplaceCategory(**data.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category_read(category)


@router.put("/admin/marketplace/categories/{category_id}", response_model=MarketplaceCategoryRead)
def update_category(
    category_id: str,
    data: MarketplaceCategoryCreate,
    _: User = Depends(marketplace_admin),
    db: Session = Depends(get_db),
) -> dict:
    category = db.get(MarketplaceCategory, category_id)
    if category is None:
        raise HTTPException(404, "Category not found.")
    conflict = db.scalar(
        select(MarketplaceCategory).where(
            MarketplaceCategory.id != category_id,
            (MarketplaceCategory.slug == data.slug) | (MarketplaceCategory.name == data.name),
        )
    )
    if conflict:
        raise HTTPException(409, "A category with this name or slug already exists.")
    for field, value in data.model_dump().items():
        setattr(category, field, value)
    db.commit()
    db.refresh(category)
    return category_read(category)


@router.get("/admin/marketplace/products", response_model=list[MarketplaceProductRead])
def admin_products(_: User = Depends(marketplace_admin), db: Session = Depends(get_db)) -> list[dict]:
    products = db.scalars(
        select(MarketplaceProduct)
        .options(joinedload(MarketplaceProduct.category))
        .order_by(MarketplaceProduct.created_at.desc())
    ).all()
    return [product_read(product) for product in products]


@router.post("/admin/marketplace/products", response_model=MarketplaceProductRead, status_code=201)
def create_product(
    data: MarketplaceProductCreate,
    _: User = Depends(marketplace_admin),
    db: Session = Depends(get_db),
) -> dict:
    category = db.get(MarketplaceCategory, data.category_id)
    if category is None:
        raise HTTPException(404, "Category not found.")
    if db.scalar(select(MarketplaceProduct).where(MarketplaceProduct.slug == data.slug)):
        raise HTTPException(409, "A product with this slug already exists.")
    product = MarketplaceProduct(**data.model_dump())
    db.add(product)
    db.commit()
    product = db.scalar(
        select(MarketplaceProduct).where(MarketplaceProduct.id == product.id).options(joinedload(MarketplaceProduct.category))
    )
    return product_read(product)


@router.put("/admin/marketplace/products/{product_id}", response_model=MarketplaceProductRead)
def update_product(
    product_id: str,
    data: MarketplaceProductCreate,
    _: User = Depends(marketplace_admin),
    db: Session = Depends(get_db),
) -> dict:
    product = db.get(MarketplaceProduct, product_id)
    if product is None:
        raise HTTPException(404, "Product not found.")
    if db.get(MarketplaceCategory, data.category_id) is None:
        raise HTTPException(404, "Category not found.")
    conflict = db.scalar(
        select(MarketplaceProduct).where(
            MarketplaceProduct.id != product_id, MarketplaceProduct.slug == data.slug
        )
    )
    if conflict:
        raise HTTPException(409, "A product with this slug already exists.")
    for field, value in data.model_dump().items():
        setattr(product, field, value)
    db.commit()
    product = db.scalar(
        select(MarketplaceProduct).where(MarketplaceProduct.id == product.id).options(joinedload(MarketplaceProduct.category))
    )
    return product_read(product)


@router.get("/admin/marketplace/orders", response_model=list[MarketplaceOrderRead])
def admin_orders(_: User = Depends(marketplace_admin), db: Session = Depends(get_db)) -> list[dict]:
    orders = db.scalars(
        select(MarketplaceOrder)
        .options(joinedload(MarketplaceOrder.user), selectinload(MarketplaceOrder.items))
        .order_by(MarketplaceOrder.created_at.desc())
        .limit(200)
    ).all()
    return [order_read(order) for order in orders]


@router.patch("/admin/marketplace/orders/{order_id}", response_model=MarketplaceOrderRead)
def admin_update_order(
    order_id: str,
    data: MarketplaceOrderStatusUpdate,
    _: User = Depends(marketplace_admin),
    db: Session = Depends(get_db),
) -> dict:
    order = db.scalar(
        select(MarketplaceOrder)
        .where(MarketplaceOrder.id == order_id)
        .options(joinedload(MarketplaceOrder.user), selectinload(MarketplaceOrder.items))
    )
    if order is None:
        raise HTTPException(404, "Order not found.")
    return order_read(update_order_status(db, order, data.status, data.admin_note))
