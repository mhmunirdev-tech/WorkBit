from decimal import Decimal
from pydantic import BaseModel


class WalletRead(BaseModel):
    id: str
    user_id: str
    available_balance: Decimal
    deposit_balance: Decimal
    earning_balance: Decimal
    reversal_debt: Decimal
    package_active: bool
    can_deposit: bool
    pending_balance: Decimal
    lifetime_earned: Decimal
    lifetime_withdrawn: Decimal
    currency: str


class WalletTransactionRead(BaseModel):
    id: str
    wallet_id: str
    user_id: str
    type: str
    amount: Decimal
    currency: str
    status: str
    reference_type: str | None = None
    reference_id: str | None = None
    description: str
    balance_before: Decimal
    balance_after: Decimal
    created_at: str


class RewardDecisionRead(BaseModel):
    id: str
    conversion_id: str
    user_id: str
    reward_policy_id: str | None = None
    provider_payout: Decimal
    user_reward: Decimal
    platform_share: Decimal
    currency: str
    status: str
    reason: str
    rule_version: str
    created_at: str
