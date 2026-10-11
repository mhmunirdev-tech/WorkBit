from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import OfferConversion, PackagePurchase, RewardDecision, RewardPolicy, User, Wallet, WalletTransaction
from app.services.fraud import fraud_service
from app.services.packages import has_active_package

ZERO = Decimal("0")


class RewardDecisionService:
    def process_conversion(self, db: Session, conversion: OfferConversion) -> RewardDecision:
        existing = db.scalar(select(RewardDecision).where(RewardDecision.conversion_id == conversion.id))
        if existing:
            return existing

        user = db.get(User, conversion.user_id)
        if not user:
            raise HTTPException(404, "Conversion user not found.")
        wallet = user.wallet
        if wallet is None:
            raise HTTPException(409, "Wallet is unavailable for this reward.")
        if conversion.currency.upper() != wallet.currency.upper():
            raise HTTPException(409, "Conversion currency does not match the user's wallet currency.")

        fraud = fraud_service.assess_conversion(False)
        policy = self._select_policy(db, user, conversion)
        if not policy:
            raise HTTPException(503, "No reward policy is configured.")

        provider_payout = conversion.provider_payout
        if provider_payout <= ZERO:
            return self._persist_decision(db, conversion, user, policy, "REJECTED", "Provider payout is zero or negative.")

        user_reward = self._calculate_user_reward(policy, provider_payout)
        platform_share = self._calculate_platform_share(policy, provider_payout)

        if fraud.action in {"FRAUD", "REJECTED"}:
            return self._persist_decision(db, conversion, user, policy, "REJECTED", f"Fraud assessment: {fraud.action}")
        if fraud.action == "MANUAL_REVIEW":
            return self._persist_decision(db, conversion, user, policy, "MANUAL_REVIEW", f"Fraud assessment: {fraud.action}")

        decision_status = self._decision_status(conversion, policy)
        decision = self._persist_decision(
            db,
            conversion,
            user,
            policy,
            decision_status,
            "Reward calculated from configured policy.",
            provider_payout=provider_payout,
            user_reward=user_reward,
            platform_share=platform_share,
        )
        self._apply_wallet_projection(db, user, decision)
        db.commit()
        db.refresh(decision)
        return decision

    def manual_decision(self, db: Session, conversion: OfferConversion, status: str, reason: str, user: User | None = None) -> RewardDecision:
        if status not in {"APPROVED", "PENDING", "REJECTED", "MANUAL_REVIEW", "REVERSED", "CHARGEBACK"}:
            raise HTTPException(400, "Unsupported reward decision status.")
        if user is None:
            user = db.get(User, conversion.user_id)
        if not user:
            raise HTTPException(404, "Conversion user not found.")
        wallet = user.wallet
        if wallet is None:
            raise HTTPException(409, "Wallet is unavailable for this reward.")
        if conversion.currency.upper() != wallet.currency.upper():
            raise HTTPException(409, "Conversion currency does not match the user's wallet currency.")
        existing = db.scalar(select(RewardDecision).where(RewardDecision.conversion_id == conversion.id))
        if existing:
            return self.transition_decision(db, existing, status, reason)
        policy = self._select_policy(db, user, conversion)
        if not policy:
            raise HTTPException(503, "No reward policy is configured.")
        user_reward = self._calculate_user_reward(policy, conversion.provider_payout)
        decision = self._persist_decision(db, conversion, user, policy, status, reason, provider_payout=conversion.provider_payout, user_reward=user_reward, platform_share=self._calculate_platform_share(policy, conversion.provider_payout))
        self._apply_wallet_projection(db, user, decision)
        db.commit(); db.refresh(decision)
        return decision

    def transition_decision(self, db: Session, decision: RewardDecision, status: str, reason: str) -> RewardDecision:
        """Record a reviewed outcome and append any required immutable ledger movements."""
        if status not in {"APPROVED", "REJECTED", "MANUAL_REVIEW", "REVERSED", "CHARGEBACK", "FRAUD"}:
            raise HTTPException(400, "Unsupported reward decision status.")
        if decision.status == status:
            return decision
        previous_status = decision.status
        allowed_transitions = {
            "PENDING": {"APPROVED", "REJECTED", "MANUAL_REVIEW", "REVERSED", "CHARGEBACK", "FRAUD"},
            "MANUAL_REVIEW": {"APPROVED", "REJECTED", "REVERSED", "CHARGEBACK", "FRAUD"},
            "APPROVED": {"REVERSED", "CHARGEBACK", "FRAUD"},
        }
        if status not in allowed_transitions.get(previous_status, set()):
            raise HTTPException(
                409,
                f"Reward cannot transition from {previous_status} to {status}.",
            )
        user = db.get(User, decision.user_id)
        wallet = user.wallet if user else None
        if wallet is None:
            raise HTTPException(409, "Wallet is unavailable for this reward.")
        if decision.currency.upper() != wallet.currency.upper():
            raise HTTPException(409, "Reward currency does not match the user's wallet currency.")
        if previous_status == "PENDING" and status == "APPROVED":
            self._settle_pending(db, wallet, decision)
        elif previous_status == "PENDING" and status in {"REJECTED", "MANUAL_REVIEW", "REVERSED", "CHARGEBACK", "FRAUD"}:
            self._cancel_pending(db, wallet, decision, status)
        elif previous_status == "APPROVED" and status in {"REVERSED", "CHARGEBACK", "FRAUD"}:
            self._reverse_available(db, wallet, decision, status)
        decision.status, decision.reason = status, reason
        if previous_status == "MANUAL_REVIEW" and status == "APPROVED":
            self._apply_wallet_projection(db, user, decision)
        decision.updated_at = datetime.now(timezone.utc)
        db.commit(); db.refresh(decision)
        return decision

    def _append_settlement(self, db: Session, wallet: Wallet, decision: RewardDecision, tx_type: str, amount: Decimal, status: str, before: Decimal, after: Decimal) -> None:
        db.add(WalletTransaction(wallet_id=wallet.id, user_id=decision.user_id, type=tx_type, amount=amount,
            currency=decision.currency, status=status, reference_type="reward_settlement",
            reference_id=f"{decision.id}:{status}", description=f"Offer reward {status.lower()}",
            metadata_json=json.dumps({"decision_id": decision.id, "source": "reward_settlement"}),
            balance_before=before, balance_after=after))

    def _settle_pending(self, db: Session, wallet: Wallet, decision: RewardDecision) -> None:
        amount = decision.user_reward
        if wallet.pending_balance < amount:
            raise HTTPException(409, "Pending balance does not cover this reward.")
        before = wallet.pending_balance
        wallet.pending_balance -= amount; wallet.available_balance += amount
        self._append_settlement(db, wallet, decision, "OFFER_REWARD_RELEASE", amount, "APPROVED", before, wallet.pending_balance)

    def _cancel_pending(self, db: Session, wallet: Wallet, decision: RewardDecision, status: str) -> None:
        amount = decision.user_reward
        if wallet.pending_balance < amount:
            raise HTTPException(409, "Pending balance does not cover this reward.")
        before = wallet.pending_balance
        wallet.pending_balance -= amount; wallet.lifetime_earned -= amount
        self._append_settlement(db, wallet, decision, "OFFER_REWARD_CANCEL", -amount, status, before, wallet.pending_balance)

    def _reverse_available(self, db: Session, wallet: Wallet, decision: RewardDecision, status: str) -> None:
        amount = decision.user_reward
        if wallet.available_balance - wallet.deposit_balance < amount:
            raise HTTPException(409, "Available balance does not cover this reversal.")
        before = wallet.available_balance
        wallet.available_balance -= amount; wallet.lifetime_earned -= amount
        self._append_settlement(db, wallet, decision, "OFFER_REWARD_REVERSAL", -amount, status, before, wallet.available_balance)

    def _persist_decision(
        self,
        db: Session,
        conversion: OfferConversion,
        user: User,
        policy: RewardPolicy,
        status: str,
        reason: str,
        provider_payout: Decimal | None = None,
        user_reward: Decimal | None = None,
        platform_share: Decimal | None = None,
    ) -> RewardDecision:
        provider_payout = provider_payout if provider_payout is not None else conversion.provider_payout
        user_reward = user_reward if user_reward is not None else self._calculate_user_reward(policy, provider_payout)
        platform_share = platform_share if platform_share is not None else provider_payout - user_reward
        decision = RewardDecision(
            conversion_id=conversion.id,
            user_id=user.id,
            reward_policy_id=policy.id,
            provider_payout=provider_payout,
            user_reward=user_reward,
            platform_share=platform_share,
            currency=conversion.currency,
            status=status,
            reason=reason,
            rule_version="v1",
            metadata_json=json.dumps({"conversion_status": conversion.status, "network_id": conversion.network_id, "offer_id": conversion.offer_id}),
        )
        db.add(decision)
        db.flush()
        return decision

    def _select_policy(self, db: Session, user: User, conversion: OfferConversion) -> RewardPolicy | None:
        candidates = db.scalars(select(RewardPolicy).where(RewardPolicy.enabled.is_(True))).all()
        candidates = [p for p in candidates if self._policy_active(p)]
        ranked: list[tuple[int, str, str, RewardPolicy]] = []
        for policy in candidates:
            if policy.country_code and policy.country_code.upper() != user.country.upper():
                continue
            if policy.network_id and policy.network_id != conversion.network_id:
                continue
            if policy.offer_id and policy.offer_id != conversion.offer_id:
                continue
            score = 0
            if policy.country_code:
                score += 4
            if policy.network_id:
                score += 3
            if policy.offer_id:
                score += 5
            ranked.append((score, policy.name, policy.id, policy))
        if not ranked:
            return None
        return min(ranked, key=lambda item: (-item[0], item[1], item[2]))[3]

    def _policy_active(self, policy: RewardPolicy) -> bool:
        now = datetime.now(timezone.utc)
        if not policy.enabled:
            return False
        effective_from = policy.effective_from
        effective_to = policy.effective_to
        if effective_from and effective_from.tzinfo is None:
            effective_from = effective_from.replace(tzinfo=timezone.utc)
        if effective_to and effective_to.tzinfo is None:
            effective_to = effective_to.replace(tzinfo=timezone.utc)
        if effective_from and effective_from > now:
            return False
        if effective_to and effective_to < now:
            return False
        return True

    def _calculate_user_reward(self, policy: RewardPolicy, provider_payout: Decimal) -> Decimal:
        if provider_payout <= ZERO:
            return ZERO
        percent = self._normalize_percentage(policy.user_reward_percentage)
        reward = provider_payout * percent
        if policy.minimum_reward and reward < policy.minimum_reward:
            reward = policy.minimum_reward
        if policy.maximum_reward and reward > policy.maximum_reward:
            reward = policy.maximum_reward
        precision = max(policy.rounding_precision, 2)
        quantum = Decimal("1").scaleb(-precision)
        return reward.quantize(quantum, rounding=ROUND_HALF_UP)

    def _calculate_platform_share(self, policy: RewardPolicy, provider_payout: Decimal) -> Decimal:
        if provider_payout <= ZERO:
            return ZERO
        percent = self._normalize_percentage(policy.platform_share_percentage)
        share = provider_payout * percent
        precision = max(policy.rounding_precision, 2)
        quantum = Decimal("1").scaleb(-precision)
        return share.quantize(quantum, rounding=ROUND_HALF_UP)

    def _normalize_percentage(self, value: Decimal) -> Decimal:
        if value <= ZERO:
            return ZERO
        if value > Decimal("1"):
            return value / Decimal("100")
        return value

    def _decision_status(self, conversion: OfferConversion, policy: RewardPolicy) -> str:
        if conversion.status in {"REJECTED", "REVERSED", "CHARGEBACK", "FRAUD"}:
            return conversion.status
        if conversion.status == "MANUAL_REVIEW":
            return "MANUAL_REVIEW"
        if conversion.status == "PENDING":
            return "PENDING"
        if conversion.status == "APPROVED":
            return "APPROVED"
        return "PENDING"

    def _apply_wallet_projection(self, db: Session, user: User, decision: RewardDecision) -> None:
        if decision.status not in {"PENDING", "APPROVED"}:
            return
        wallet = user.wallet or db.scalar(select(Wallet).where(Wallet.user_id == user.id))
        if wallet is None:
            wallet = Wallet(user_id=user.id, currency=decision.currency)
            db.add(wallet)
            db.flush()
            user.wallet = wallet
        amount = decision.user_reward
        if decision.status == "PENDING":
            before = wallet.pending_balance
            wallet.pending_balance += amount
            wallet.lifetime_earned += amount
            tx = WalletTransaction(
                wallet_id=wallet.id,
                user_id=user.id,
                type="OFFER_REWARD_PENDING",
                amount=amount,
                currency=decision.currency,
                status="PENDING",
                reference_type="reward_decision",
                reference_id=decision.id,
                description="Pending offer reward",
                metadata_json=json.dumps({"decision_id": decision.id, "source": "offer_reward"}),
                balance_before=before,
                balance_after=wallet.pending_balance,
            )
            db.add(tx)
            return

        before_available = wallet.available_balance
        wallet.available_balance += amount
        wallet.lifetime_earned += amount
        tx = WalletTransaction(
            wallet_id=wallet.id,
            user_id=user.id,
            type="OFFER_REWARD_APPROVAL",
            amount=amount,
            currency=decision.currency,
            status="APPROVED",
            reference_type="reward_decision",
            reference_id=decision.id,
            description="Approved offer reward",
            metadata_json=json.dumps({"decision_id": decision.id, "source": "offer_reward"}),
            balance_before=before_available,
            balance_after=wallet.available_balance,
        )
        db.add(tx)


class WalletService:
    def wallet_snapshot(self, db: Session, user: User) -> dict:
        wallet = user.wallet or db.scalar(select(Wallet).where(Wallet.user_id == user.id))
        if wallet is None:
            wallet = Wallet(user_id=user.id, currency="USD")
            db.add(wallet); db.flush()
            user.wallet = wallet
        latest_purchase = db.scalar(
            select(PackagePurchase)
            .where(PackagePurchase.user_id == user.id)
            .order_by(PackagePurchase.created_at.desc())
            .limit(1)
        )
        package_active = has_active_package(db, user.id)
        return {
            "id": wallet.id,
            "user_id": wallet.user_id,
            "available_balance": str(wallet.available_balance),
            "deposit_balance": str(wallet.deposit_balance),
            "earning_balance": str(wallet.available_balance - wallet.deposit_balance),
            "package_active": package_active,
            "can_deposit": bool(
                user.status == "ACTIVE"
                and user.email_verified
                and not package_active
                and (latest_purchase is None or latest_purchase.status != "PENDING")
            ),
            "pending_balance": str(wallet.pending_balance),
            "lifetime_earned": str(wallet.lifetime_earned),
            "lifetime_withdrawn": str(wallet.lifetime_withdrawn),
            "currency": wallet.currency,
        }

    def wallet_transactions(self, db: Session, user: User) -> list[WalletTransaction]:
        return db.scalars(select(WalletTransaction).where(WalletTransaction.user_id == user.id).order_by(WalletTransaction.created_at.desc())).all()


reward_decision_service = RewardDecisionService()
wallet_service = WalletService()
