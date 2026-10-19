from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import current_user, require_permission
from app.database.session import get_db
from app.models import RewardDecision, User, UserPayoutAccount
from app.schemas.wallet import RewardDecisionRead, WalletRead, WalletTransactionRead
from app.schemas.withdrawals import PayoutAccountCreate, PayoutAccountOtpRequest, PayoutAccountRead
from app.services.auth import consume_action_code, issue_action_code
from app.services.email import EmailDeliveryError, email_service
from app.services.rate_limit import enforce_cooldown
from app.services.rewards import reward_decision_service, wallet_service
from app.services.withdrawals import withdrawal_service

router = APIRouter(tags=["wallet"])
PAYOUT_ACCOUNT_OTP_PURPOSE = "PAYOUT_ACCOUNT"
OTP_RESEND_COOLDOWN_SECONDS = 60


def _account_code_context(method: str, destination: str, account_id: str | None) -> str:
    return f"{method}:{destination}:{account_id or 'new'}"


def _account_read(account: UserPayoutAccount) -> dict:
    return {
        "id": account.id,
        "method": account.method,
        "destination_hint": account.destination_hint,
        "updated_at": account.updated_at,
    }


@router.get("/wallet", response_model=WalletRead)
def wallet(user: User = Depends(current_user), db: Session = Depends(get_db)) -> WalletRead:
    data = wallet_service.wallet_snapshot(db, user)
    return WalletRead(**data)


@router.get("/wallet/payout-accounts", response_model=list[PayoutAccountRead])
def payout_accounts(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    return [
        _account_read(item)
        for item in withdrawal_service.list_payout_accounts(db, user)
    ]


@router.post("/wallet/payout-accounts/otp", status_code=202)
def send_payout_account_otp(
    data: PayoutAccountOtpRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    if not user.email_verified or user.status != "ACTIVE":
        raise HTTPException(403, "An active, verified account is required.")
    if data.account_id is None:
        count = db.scalar(
            select(func.count())
            .select_from(UserPayoutAccount)
            .where(
                UserPayoutAccount.user_id == user.id,
                UserPayoutAccount.method == data.method,
            )
        )
        if count >= 2:
            raise HTTPException(409, f"You can save up to two {data.method.title()} accounts.")
    else:
        account = db.scalar(
            select(UserPayoutAccount).where(
                UserPayoutAccount.id == data.account_id,
                UserPayoutAccount.user_id == user.id,
                UserPayoutAccount.method == data.method,
            )
        )
        if account is None:
            raise HTTPException(404, "Saved payout account not found.")
    enforce_cooldown(
        f"payout-account-otp:{user.id}",
        seconds=OTP_RESEND_COOLDOWN_SECONDS,
        message="Please wait before requesting another confirmation code.",
    )
    context = _account_code_context(data.method, data.destination, data.account_id)
    code = issue_action_code(db, user, PAYOUT_ACCOUNT_OTP_PURPOSE, context)
    try:
        email_service.send_security_code(user.email, code, "payout account change")
    except EmailDeliveryError as error:
        db.rollback()
        raise HTTPException(503, "The confirmation email could not be delivered. Please try again later.") from error
    db.commit()
    return {"message": "A confirmation code has been sent to your registered email."}


@router.post("/wallet/payout-accounts", response_model=PayoutAccountRead)
def save_payout_account(
    data: PayoutAccountCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    context = _account_code_context(data.method, data.destination, data.account_id)
    consume_action_code(db, user, PAYOUT_ACCOUNT_OTP_PURPOSE, context, data.code)
    account = withdrawal_service.save_payout_account(
        db, user, data.method, data.destination, data.account_id
    )
    return _account_read(account)


@router.delete("/wallet/payout-accounts/{account_id}", status_code=204)
def delete_payout_account(
    account_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Response:
    withdrawal_service.delete_payout_account(db, user, account_id)
    return Response(status_code=204)


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
