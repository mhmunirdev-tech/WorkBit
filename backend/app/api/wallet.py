from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user, require_permission
from app.database.session import get_db
from app.models import RewardDecision, User, Wallet, WalletTransaction
from app.schemas.wallet import RewardDecisionRead, WalletRead, WalletTransactionRead
from app.services.rewards import reward_decision_service, wallet_service

router = APIRouter(tags=["wallet"])


@router.get("/wallet", response_model=WalletRead)
def wallet(user: User = Depends(current_user), db: Session = Depends(get_db)) -> WalletRead:
    data = wallet_service.wallet_snapshot(db, user)
    return WalletRead(**data)


@router.get("/wallet/transactions", response_model=list[WalletTransactionRead])
def wallet_transactions(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[WalletTransactionRead]:
    txs = wallet_service.wallet_transactions(db, user)
    return [
        WalletTransactionRead(
            id=item.id,
            wallet_id=item.wallet_id,
            user_id=item.user_id,
            type=item.type,
            amount=item.amount,
            currency=item.currency,
            status=item.status,
            reference_type=item.reference_type,
            reference_id=item.reference_id,
            description=item.description,
            balance_before=item.balance_before,
            balance_after=item.balance_after,
            created_at=item.created_at.isoformat(),
        )
        for item in txs
    ]


@router.get("/rewards", response_model=list[RewardDecisionRead])
def rewards(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[RewardDecisionRead]:
    decisions = db.scalars(select(RewardDecision).where(RewardDecision.user_id == user.id).order_by(RewardDecision.created_at.desc())).all()
    return [
        RewardDecisionRead(
            id=item.id,
            conversion_id=item.conversion_id,
            user_id=item.user_id,
            reward_policy_id=item.reward_policy_id,
            provider_payout=item.provider_payout,
            user_reward=item.user_reward,
            platform_share=item.platform_share,
            currency=item.currency,
            status=item.status,
            reason=item.reason,
            rule_version=item.rule_version,
            created_at=item.created_at.isoformat(),
        )
        for item in decisions
    ]


@router.get("/rewards/{reward_id}", response_model=RewardDecisionRead)
def reward_detail(reward_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> RewardDecisionRead:
    decision = db.scalar(select(RewardDecision).where(RewardDecision.id == reward_id, RewardDecision.user_id == user.id))
    if not decision:
        raise HTTPException(404, "Reward decision not found.")
    return RewardDecisionRead(
        id=decision.id,
        conversion_id=decision.conversion_id,
        user_id=decision.user_id,
        reward_policy_id=decision.reward_policy_id,
        provider_payout=decision.provider_payout,
        user_reward=decision.user_reward,
        platform_share=decision.platform_share,
        currency=decision.currency,
        status=decision.status,
        reason=decision.reason,
        rule_version=decision.rule_version,
        created_at=decision.created_at.isoformat(),
    )


@router.post("/admin/rewards/{reward_id}/approve")
def approve_reward(reward_id: str, _: User = Depends(require_permission("wallets.view")), db: Session = Depends(get_db)) -> dict[str, str]:
    decision = db.get(RewardDecision, reward_id)
    if not decision:
        raise HTTPException(404, "Reward decision not found.")
    decision = reward_decision_service.transition_decision(db, decision, "APPROVED", "Manual approval by admin review.")
    return {"status": decision.status, "reward_id": decision.id}


@router.post("/admin/rewards/{reward_id}/reject")
def reject_reward(reward_id: str, _: User = Depends(require_permission("wallets.view")), db: Session = Depends(get_db)) -> dict[str, str]:
    decision = db.get(RewardDecision, reward_id)
    if not decision:
        raise HTTPException(404, "Reward decision not found.")
    decision = reward_decision_service.transition_decision(db, decision, "REJECTED", "Manual rejection by admin review.")
    return {"status": decision.status, "reward_id": decision.id}
