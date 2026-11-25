import json
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import (
    MarketplaceCart,
    MarketplaceCartItem,
    MarketplaceCategory,
    MarketplaceOrder,
    MarketplaceOrderItem,
    MarketplaceProduct,
    PayoutSettings,
    User,
    Wallet,
    WalletTransaction,
)
from app.schemas.marketplace import MarketplaceOrderCreate

DELIVERY_FEE = Decimal("0.00")
AFFILIATE_RATE = Decimal("0.0500")
AFFILIATE_REWARD_TYPE = "MARKETPLACE_AFFILIATE_REWARD"
AFFILIATE_PRECISION = Decimal("0.00000001")
ORDER_STATUS_TRANSITIONS = {
    "PENDING": {"CONFIRMED", "CANCELLED"},
    "CONFIRMED": {"PROCESSING", "CANCELLED"},
    "PROCESSING": {"SHIPPED", "CANCELLED"},
    "SHIPPED": {"DELIVERED"},
    "DELIVERED": set(),
    "CANCELLED": set(),
}


def category_read(category: MarketplaceCategory, product_count: int = 0) -> dict:
    return {
        "id": category.id,
        "name": category.name,
        "slug": category.slug,
        "description": category.description,
        "is_active": category.is_active,
        "sort_order": category.sort_order,
        "product_count": product_count,
    }


def product_read(product: MarketplaceProduct) -> dict:
    return {
        "id": product.id,
        "category_id": product.category_id,
        "category_name": product.category.name,
        "category_slug": product.category.slug,
        "sku": product.sku,
        "name": product.name,
        "slug": product.slug,
        "description": product.description,
        "image_url": product.image_url,
        "price": product.price,
        "currency": product.currency,
        "stock_quantity": product.stock_quantity,
        "is_active": product.is_active,
        "featured": product.featured,
        "sort_order": product.sort_order,
        "created_at": product.created_at,
        "updated_at": product.updated_at,
    }


def _cart_item_read(item: MarketplaceCartItem) -> dict:
    product = item.product
    return {
        "id": item.id,
        "product_id": product.id,
        "product_name": product.name,
        "slug": product.slug,
        "image_url": product.image_url,
        "price": product.price,
        "currency": product.currency,
        "stock_quantity": product.stock_quantity,
        "quantity": item.quantity,
        "line_total": product.price * item.quantity,
    }


def cart_read(cart: MarketplaceCart | None) -> dict:
    items = [_cart_item_read(item) for item in (cart.items if cart else [])]
    subtotal = sum((item["line_total"] for item in items), Decimal("0.00"))
    currency = items[0]["currency"] if items else "BDT"
    return {"items": items, "subtotal": subtotal, "currency": currency}


def get_or_create_cart(db: Session, user: User) -> MarketplaceCart:
    cart = db.scalar(
        select(MarketplaceCart)
        .where(MarketplaceCart.user_id == user.id)
        .options(
            selectinload(MarketplaceCart.items).joinedload(MarketplaceCartItem.product).joinedload(
                MarketplaceProduct.category
            )
        )
    )
    if cart is None:
        cart = MarketplaceCart(user_id=user.id)
        db.add(cart)
        db.flush()
    return cart


def order_read(order: MarketplaceOrder) -> dict:
    return {
        "id": order.id,
        "status": order.status,
        "payment_method": order.payment_method,
        "subtotal": order.subtotal,
        "delivery_fee": order.delivery_fee,
        "total": order.total,
        "currency": order.currency,
        "shipping_name": order.shipping_name,
        "shipping_phone": order.shipping_phone,
        "shipping_address": order.shipping_address,
        "shipping_city": order.shipping_city,
        "customer_note": order.customer_note,
        "admin_note": order.admin_note,
        "affiliate_referrer_id": order.affiliate_referrer_id,
        "affiliate_rate": order.affiliate_rate,
        "affiliate_commission_bdt": order.affiliate_commission_bdt,
        "affiliate_reward_amount": order.affiliate_reward_amount,
        "affiliate_exchange_rate": order.affiliate_exchange_rate,
        "affiliate_reward_status": order.affiliate_reward_status,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
        "items": [
            {
                "id": item.id,
                "product_id": item.product_id,
                "product_name": item.product_name,
                "sku": item.sku,
                "unit_price": item.unit_price,
                "quantity": item.quantity,
                "line_total": item.line_total,
            }
            for item in order.items
        ],
        "user_id": order.user_id,
        "user_name": order.user.full_name if order.user else None,
        "user_email": order.user.email if order.user else None,
    }


def create_order(db: Session, user: User, data: MarketplaceOrderCreate) -> MarketplaceOrder:
    cart = get_or_create_cart(db, user)
    if not cart.items:
        raise HTTPException(400, "Your cart is empty.")

    products: list[tuple[MarketplaceCartItem, MarketplaceProduct]] = []
    for cart_item in cart.items:
        product = db.scalar(
            select(MarketplaceProduct)
            .where(MarketplaceProduct.id == cart_item.product_id)
            .with_for_update()
        )
        if product is None or not product.is_active or not product.category.is_active:
            raise HTTPException(409, "One of the products is no longer available.")
        if product.stock_quantity < cart_item.quantity:
            raise HTTPException(409, f"Not enough stock for {product.name}.")
        products.append((cart_item, product))

    subtotal = sum(
        (product.price * cart_item.quantity for cart_item, product in products),
        Decimal("0.00"),
    )
    referrer = None
    if data.referral_code and data.referral_code.strip():
        normalized_code = data.referral_code.strip().upper()
        referrer = db.scalar(
            select(User).where(
                (User.referral_code == normalized_code)
                | (User.legacy_referral_code == normalized_code)
            )
        )
        if referrer is None:
            raise HTTPException(400, "The product referral code is invalid.")
        if referrer.id == user.id or referrer.status != "ACTIVE":
            referrer = None
    affiliate_commission_bdt = (
        (subtotal * AFFILIATE_RATE).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if referrer
        else Decimal("0.00")
    )
    order = MarketplaceOrder(
        user_id=user.id,
        affiliate_referrer_id=referrer.id if referrer else None,
        affiliate_rate=AFFILIATE_RATE,
        affiliate_commission_bdt=affiliate_commission_bdt,
        affiliate_reward_status="PENDING" if referrer and affiliate_commission_bdt > 0 else "NOT_ELIGIBLE",
        status="PENDING",
        payment_method=data.payment_method,
        subtotal=subtotal,
        delivery_fee=DELIVERY_FEE,
        total=subtotal + DELIVERY_FEE,
        currency="BDT",
        shipping_name=data.shipping_name,
        shipping_phone=data.shipping_phone,
        shipping_address=data.shipping_address,
        shipping_city=data.shipping_city,
        customer_note=data.customer_note.strip(),
    )
    db.add(order)
    db.flush()
    for cart_item, product in products:
        product.stock_quantity -= cart_item.quantity
        db.add(
            MarketplaceOrderItem(
                order_id=order.id,
                product_id=product.id,
                product_name=product.name,
                sku=product.sku,
                unit_price=product.price,
                quantity=cart_item.quantity,
                line_total=product.price * cart_item.quantity,
            )
        )
        db.delete(cart_item)
    db.commit()
    db.refresh(order)
    return db.scalar(
        select(MarketplaceOrder)
        .where(MarketplaceOrder.id == order.id)
        .options(selectinload(MarketplaceOrder.items), joinedload(MarketplaceOrder.user))
    ) or order


def credit_affiliate_reward(db: Session, order: MarketplaceOrder) -> None:
    if order.affiliate_reward_status != "PENDING" or not order.affiliate_referrer_id:
        return
    existing = db.scalar(
        select(WalletTransaction.id).where(
            WalletTransaction.type == AFFILIATE_REWARD_TYPE,
            WalletTransaction.reference_type == "marketplace_order",
            WalletTransaction.reference_id == order.id,
        )
    )
    if existing:
        order.affiliate_reward_status = "CREDITED"
        return
    payout_settings = db.get(PayoutSettings, "default")
    exchange_rate = payout_settings.usd_bdt_rate if payout_settings else None
    if exchange_rate is None or exchange_rate <= 0:
        raise HTTPException(503, "Set the USD to BDT exchange rate before completing affiliate rewards.")
    referrer_wallet = db.scalar(
        select(Wallet)
        .where(Wallet.user_id == order.affiliate_referrer_id)
        .with_for_update()
    )
    if referrer_wallet is None:
        referrer_wallet = Wallet(user_id=order.affiliate_referrer_id, currency="USD")
        db.add(referrer_wallet)
        db.flush()
    commission_usd = (order.affiliate_commission_bdt / exchange_rate).quantize(
        AFFILIATE_PRECISION, rounding=ROUND_HALF_UP
    )
    if commission_usd <= 0:
        order.affiliate_reward_status = "NOT_ELIGIBLE"
        return
    before = referrer_wallet.available_balance
    referrer_wallet.available_balance += commission_usd
    referrer_wallet.lifetime_earned += commission_usd
    db.add(
        WalletTransaction(
            wallet_id=referrer_wallet.id,
            user_id=referrer_wallet.user_id,
            type=AFFILIATE_REWARD_TYPE,
            amount=commission_usd,
            currency=referrer_wallet.currency,
            status="APPROVED",
            reference_type="marketplace_order",
            reference_id=order.id,
            description="5% product affiliate reward",
            metadata_json=json.dumps(
                {
                    "order_id": order.id,
                    "buyer_user_id": order.user_id,
                    "commission_bdt": str(order.affiliate_commission_bdt),
                    "exchange_rate": str(exchange_rate),
                    "affiliate_rate": str(order.affiliate_rate),
                }
            ),
            balance_before=before,
            balance_after=referrer_wallet.available_balance,
        )
    )
    order.affiliate_exchange_rate = exchange_rate
    order.affiliate_reward_amount = commission_usd
    order.affiliate_reward_status = "CREDITED"


def update_order_status(
    db: Session, order: MarketplaceOrder, status: str, admin_note: str | None
) -> MarketplaceOrder:
    if status == order.status:
        order.admin_note = admin_note.strip() if admin_note else None
        db.commit()
        db.refresh(order)
        return order
    if status not in ORDER_STATUS_TRANSITIONS.get(order.status, set()):
        raise HTTPException(409, f"An order cannot move from {order.status} to {status}.")
    if status == "CANCELLED":
        for item in order.items:
            product = db.get(MarketplaceProduct, item.product_id)
            if product:
                product.stock_quantity += item.quantity
        if order.affiliate_reward_status == "PENDING":
            order.affiliate_reward_status = "CANCELLED"
    order.status = status
    order.admin_note = admin_note.strip() if admin_note else None
    if status == "DELIVERED":
        credit_affiliate_reward(db, order)
    db.commit()
    db.refresh(order)
    return db.scalar(
        select(MarketplaceOrder)
        .where(MarketplaceOrder.id == order.id)
        .options(selectinload(MarketplaceOrder.items), joinedload(MarketplaceOrder.user))
    ) or order
