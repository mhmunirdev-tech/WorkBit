from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def clean_text(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("This field cannot be empty.")
    return value


class MarketplaceCategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    slug: str = Field(min_length=1, max_length=96, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    description: str = Field(default="", max_length=500)
    is_active: bool = True
    sort_order: int = Field(default=0, ge=0, le=10000)

    _clean_name = field_validator("name")(clean_text)


class MarketplaceCategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    description: str
    is_active: bool
    sort_order: int
    product_count: int = 0


class MarketplaceProductCreate(BaseModel):
    category_id: str = Field(min_length=1, max_length=36)
    sku: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=160)
    slug: str = Field(min_length=1, max_length=180, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    description: str = Field(default="", max_length=5000)
    image_url: str | None = Field(default=None, max_length=1024)
    image_url_2: str | None = Field(default=None, max_length=1024)
    image_url_3: str | None = Field(default=None, max_length=1024)
    video_url: str | None = Field(default=None, max_length=1024)
    price: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    currency: Literal["BDT"] = "BDT"
    stock_quantity: int = Field(default=0, ge=0, le=2_000_000_000)
    is_active: bool = False
    featured: bool = False
    sort_order: int = Field(default=0, ge=0, le=10000)

    _clean_name = field_validator("name", "sku")(clean_text)


class MarketplaceProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    category_id: str
    category_name: str
    category_slug: str
    sku: str
    name: str
    slug: str
    description: str
    image_url: str | None
    image_url_2: str | None
    image_url_3: str | None
    video_url: str | None
    price: Decimal
    currency: str
    stock_quantity: int
    is_active: bool
    featured: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


class MarketplaceCartItemAdd(BaseModel):
    product_id: str = Field(min_length=1, max_length=36)
    quantity: int = Field(default=1, ge=1, le=99)


class MarketplaceCartItemUpdate(BaseModel):
    quantity: int = Field(ge=1, le=99)


class MarketplaceCartItemRead(BaseModel):
    id: str
    product_id: str
    product_name: str
    slug: str
    image_url: str | None
    price: Decimal
    currency: str
    stock_quantity: int
    quantity: int
    line_total: Decimal


class MarketplaceCartRead(BaseModel):
    items: list[MarketplaceCartItemRead]
    subtotal: Decimal
    currency: str


class MarketplaceOrderCreate(BaseModel):
    shipping_name: str = Field(min_length=2, max_length=120)
    shipping_phone: str = Field(min_length=7, max_length=32)
    shipping_address: str = Field(min_length=5, max_length=500)
    shipping_city: str = Field(min_length=2, max_length=80)
    customer_note: str = Field(default="", max_length=500)
    payment_method: Literal["COD"] = "COD"
    referral_code: str | None = Field(default=None, max_length=20)

    _clean_fields = field_validator("shipping_name", "shipping_phone", "shipping_address", "shipping_city")(clean_text)


class MarketplaceOrderItemRead(BaseModel):
    id: str
    product_id: str
    product_name: str
    sku: str
    unit_price: Decimal
    quantity: int
    line_total: Decimal


class MarketplaceOrderRead(BaseModel):
    id: str
    status: str
    payment_method: str
    subtotal: Decimal
    delivery_fee: Decimal
    total: Decimal
    currency: str
    shipping_name: str
    shipping_phone: str
    shipping_address: str
    shipping_city: str
    customer_note: str
    admin_note: str | None
    affiliate_referrer_id: str | None = None
    affiliate_rate: Decimal = Decimal("0.05")
    affiliate_commission_bdt: Decimal = Decimal("0")
    affiliate_reward_amount: Decimal = Decimal("0")
    affiliate_exchange_rate: Decimal | None = None
    affiliate_reward_status: str = "NOT_ELIGIBLE"
    created_at: datetime
    updated_at: datetime
    items: list[MarketplaceOrderItemRead]
    user_id: str | None = None
    user_name: str | None = None
    user_email: str | None = None


class MarketplaceOrderStatusUpdate(BaseModel):
    status: Literal["PENDING", "CONFIRMED", "PROCESSING", "SHIPPED", "DELIVERED", "CANCELLED"]
    admin_note: str | None = Field(default=None, max_length=500)
