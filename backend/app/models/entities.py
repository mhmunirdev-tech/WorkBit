from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from uuid import uuid4
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Table, Column, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import event
from app.database.base import Base

def now() -> datetime: return datetime.now(timezone.utc)
def uuid() -> str: return str(uuid4())

class UserStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    SUSPENDED = "SUSPENDED"
    BANNED = "BANNED"
    PENDING_REVIEW = "PENDING_REVIEW"

user_roles = Table("user_roles", Base.metadata,
    Column("user_id", String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", String(36), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)
role_permissions = Table("role_permissions", Base.metadata,
    Column("role_id", String(36), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", String(36), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120))
    country: Mapped[str] = mapped_column(String(2))
    referral_code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    referred_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default=UserStatus.PENDING_VERIFICATION.value)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    profile: Mapped[Profile] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    wallet: Mapped[Wallet] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    roles: Mapped[list[Role]] = relationship(secondary=user_roles, back_populates="users")

class Profile(Base):
    __tablename__ = "profiles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    avatar_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    user: Mapped[User] = relationship(back_populates="profile")


class DashboardBanner(Base):
    __tablename__ = "dashboard_banners"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid)
    title: Mapped[str] = mapped_column(String(120))
    content: Mapped[str] = mapped_column(String(500), default="")
    image_url: Mapped[str] = mapped_column(String(1024))
    link_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    sort_order: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid)
    name: Mapped[str] = mapped_column(String(32), unique=True)
    description: Mapped[str] = mapped_column(String(255), default="")
    users: Mapped[list[User]] = relationship(secondary=user_roles, back_populates="roles")
    permissions: Mapped[list[Permission]] = relationship(secondary=role_permissions, back_populates="roles")

class Permission(Base):
    __tablename__ = "permissions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    roles: Mapped[list[Role]] = relationship(secondary=role_permissions, back_populates="permissions")

class Wallet(Base):
    __tablename__ = "wallets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    available_balance: Mapped[Decimal] = mapped_column(Numeric(18, 8), default=Decimal("0"))
    pending_balance: Mapped[Decimal] = mapped_column(Numeric(18, 8), default=Decimal("0"))
    lifetime_earned: Mapped[Decimal] = mapped_column(Numeric(18, 8), default=Decimal("0"))
    lifetime_withdrawn: Mapped[Decimal] = mapped_column(Numeric(18, 8), default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    user: Mapped[User] = relationship(back_populates="wallet")
    transactions: Mapped[list[WalletTransaction]] = relationship(back_populates="wallet")

    @property
    def available_balance_projection(self) -> Decimal:
        return self.available_balance

    @property
    def pending_balance_projection(self) -> Decimal:
        return self.pending_balance

    @property
    def lifetime_earned_projection(self) -> Decimal:
        return self.lifetime_earned

    @property
    def lifetime_withdrawn_projection(self) -> Decimal:
        return self.lifetime_withdrawn

class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"
    __table_args__ = (
        UniqueConstraint("reference_type", "reference_id", "type", name="uq_wallet_tx_reference_type"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid)
    wallet_id: Mapped[str] = mapped_column(String(36), ForeignKey("wallets.id"))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    type: Mapped[str] = mapped_column(String(64))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 8))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    status: Mapped[str] = mapped_column(String(32))
    reference_type: Mapped[str | None] = mapped_column(String(64))
    reference_id: Mapped[str | None] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(String(255), default="")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    balance_before: Mapped[Decimal] = mapped_column(Numeric(18, 8))
    balance_after: Mapped[Decimal] = mapped_column(Numeric(18, 8))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    wallet: Mapped[Wallet] = relationship(back_populates="transactions")
    user: Mapped[User] = relationship()

    @property
    def balance_state(self) -> str:
        return self.status


class WithdrawalRequest(Base):
    __tablename__ = "withdrawal_requests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 8))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    method: Mapped[str] = mapped_column(String(32), default="MANUAL")
    destination_ciphertext: Mapped[str] = mapped_column(Text)
    destination_hint: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True)
    admin_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    user: Mapped[User] = relationship(foreign_keys=[user_id])
    reviewer: Mapped[User | None] = relationship(foreign_keys=[reviewed_by])


@event.listens_for(WalletTransaction, "before_update")
def prevent_wallet_transaction_update(_mapper, _connection, _target) -> None:
    raise ValueError("Wallet transactions are immutable; append a compensating transaction.")


@event.listens_for(WalletTransaction, "before_delete")
def prevent_wallet_transaction_delete(_mapper, _connection, _target) -> None:
    raise ValueError("Wallet transactions are immutable and cannot be deleted.")

class AuthToken(Base):
    __tablename__ = "auth_tokens"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    purpose: Mapped[str] = mapped_column(String(32), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class AdminLog(Base):
    __tablename__ = "admin_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid)
    admin_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(80))
    target_type: Mapped[str] = mapped_column(String(64))
    target_id: Mapped[str | None] = mapped_column(String(64))
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class OfferNetwork(Base):
    __tablename__ = "offer_networks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    provider: Mapped[str] = mapped_column(String(64))
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    api_base_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    api_key_env: Mapped[str | None] = mapped_column(String(128), nullable=True)
    publisher_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    placement_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    secret_key_env: Mapped[str | None] = mapped_column(String(128), nullable=True)
    postback_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    integration_type: Mapped[str] = mapped_column(String(32), default="OFFERWALL")
    country_support: Mapped[str] = mapped_column(Text, default="[]")
    device_support: Mapped[str] = mapped_column(Text, default="[]")
    priority: Mapped[int] = mapped_column(default=100)
    status: Mapped[str] = mapped_column(String(32), default="NOT_CONFIGURED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class AdNetwork(Base):
    __tablename__ = "ad_networks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    integration_type: Mapped[str] = mapped_column(String(32), default="DISPLAY")
    api_base_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    api_key_env: Mapped[str | None] = mapped_column(String(128), nullable=True)
    secret_key_env: Mapped[str | None] = mapped_column(String(128), nullable=True)
    publisher_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    placement_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country_support: Mapped[str] = mapped_column(Text, default="[]")
    device_support: Mapped[str] = mapped_column(Text, default="[]")
    priority: Mapped[int] = mapped_column(default=100)
    status: Mapped[str] = mapped_column(String(32), default="NOT_CONFIGURED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)

class Offer(Base):
    __tablename__ = "offers"
    __table_args__ = (UniqueConstraint("network_id", "external_offer_id", name="uq_offer_network_external"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid)
    network_id: Mapped[str] = mapped_column(String(36), ForeignKey("offer_networks.id"), index=True)
    external_offer_id: Mapped[str] = mapped_column(String(128))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    short_description: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(32), index=True)
    image_url: Mapped[str | None] = mapped_column(String(1024))
    tracking_url: Mapped[str | None] = mapped_column(String(2048))
    country: Mapped[str] = mapped_column(String(2), default="US")
    device_type: Mapped[str] = mapped_column(String(32), default="WEB")
    payout: Mapped[Decimal] = mapped_column(Numeric(18, 8))
    user_reward: Mapped[Decimal] = mapped_column(Numeric(18, 8))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    requirements: Mapped[str] = mapped_column(Text, default="")
    estimated_time_minutes: Mapped[int] = mapped_column(default=0)
    difficulty: Mapped[str] = mapped_column(String(32), default="Easy")
    status: Mapped[str] = mapped_column(String(32), default="DRAFT")
    featured: Mapped[bool] = mapped_column(Boolean, default=False)
    priority: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)

class OfferClick(Base):
    __tablename__ = "offer_clicks"
    __table_args__ = (UniqueConstraint("click_id", name="uq_offer_click_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    offer_id: Mapped[str] = mapped_column(String(128), index=True)
    network_id: Mapped[str] = mapped_column(String(128))
    external_offer_id: Mapped[str] = mapped_column(String(128))
    click_id: Mapped[str] = mapped_column(String(64))
    sub_id: Mapped[str] = mapped_column(String(64))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(512))
    device_type: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class OfferConversion(Base):
    __tablename__ = "offer_conversions"
    __table_args__ = (UniqueConstraint("network_id", "external_transaction_id", name="uq_conversion_network_transaction"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid)
    network_id: Mapped[str] = mapped_column(String(128), index=True)
    external_transaction_id: Mapped[str] = mapped_column(String(128))
    click_id: Mapped[str] = mapped_column(String(64), index=True)
    offer_id: Mapped[str] = mapped_column(String(128))
    external_offer_id: Mapped[str] = mapped_column(String(128))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    provider_payout: Mapped[Decimal] = mapped_column(Numeric(18, 8))
    currency: Mapped[str] = mapped_column(String(3))
    status: Mapped[str] = mapped_column(String(32), index=True)
    raw_metadata: Mapped[str] = mapped_column(Text, default="{}")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)

class RewardPolicy(Base):
    __tablename__ = "reward_policies"
    __table_args__ = (UniqueConstraint("name", name="uq_reward_policy_name"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid)
    name: Mapped[str] = mapped_column(String(120), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    user_reward_percentage: Mapped[Decimal] = mapped_column(Numeric(18, 8), default=Decimal("0.00"))
    platform_share_percentage: Mapped[Decimal] = mapped_column(Numeric(18, 8), default=Decimal("0.00"))
    minimum_reward: Mapped[Decimal] = mapped_column(Numeric(18, 8), default=Decimal("0.00"))
    maximum_reward: Mapped[Decimal] = mapped_column(Numeric(18, 8), default=Decimal("0.00"))
    pending_period_days: Mapped[int] = mapped_column(default=0)
    rounding_precision: Mapped[int] = mapped_column(default=2)
    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True, index=True)
    network_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    offer_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    decisions: Mapped[list[RewardDecision]] = relationship(back_populates="policy")

class RewardDecision(Base):
    __tablename__ = "reward_decisions"
    __table_args__ = (UniqueConstraint("conversion_id", name="uq_reward_decision_conversion"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid)
    conversion_id: Mapped[str] = mapped_column(String(36), ForeignKey("offer_conversions.id", ondelete="CASCADE"), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    reward_policy_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("reward_policies.id", ondelete="SET NULL"), nullable=True, index=True)
    provider_payout: Mapped[Decimal] = mapped_column(Numeric(18, 8), default=Decimal("0.00"))
    user_reward: Mapped[Decimal] = mapped_column(Numeric(18, 8), default=Decimal("0.00"))
    platform_share: Mapped[Decimal] = mapped_column(Numeric(18, 8), default=Decimal("0.00"))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    rule_version: Mapped[str] = mapped_column(String(64), default="v1")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    conversion: Mapped[OfferConversion] = relationship()
    user: Mapped[User] = relationship()
    policy: Mapped[RewardPolicy | None] = relationship(back_populates="decisions")
