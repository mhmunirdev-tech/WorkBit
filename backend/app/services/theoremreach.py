from __future__ import annotations

import hashlib
import json

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.integrations.offer_providers.theoremreach import (
    THEOREMREACH_SLUG,
    TheoremReachCallback,
)
from app.models import OfferConversion, RewardDecision, User, Wallet
from app.services.rewards import reward_decision_service


class TheoremReachConversionService:
    def process_callback(self, db: Session, callback: TheoremReachCallback) -> None:
        if callback.debug:
            return

        user = db.get(User, callback.user_id)
        if user is None:
            raise HTTPException(400, "Unknown TheoremReach user.")
        wallet = db.scalar(
            select(Wallet).where(Wallet.user_id == user.id).with_for_update()
        )
        if wallet is None:
            raise HTTPException(409, "User wallet is unavailable.")
        if wallet.currency.upper() != "USD":
            raise HTTPException(409, "TheoremReach payout does not match the user's USD wallet.")

        conversion = db.scalar(
            select(OfferConversion)
            .where(
                OfferConversion.network_id == THEOREMREACH_SLUG,
                OfferConversion.external_transaction_id == callback.transaction_id,
            )
            .with_for_update()
        )
        if callback.reversal:
            self._reverse(db, conversion, callback)
            return
        self._credit(db, conversion, user, callback)

    def _credit(
        self,
        db: Session,
        conversion: OfferConversion | None,
        user: User,
        callback: TheoremReachCallback,
    ) -> None:
        if conversion is not None:
            self._validate_existing_conversion(conversion, callback)
            if db.scalar(
                select(RewardDecision).where(RewardDecision.conversion_id == conversion.id)
            ) is None:
                reward_decision_service.process_conversion(db, conversion)
            return

        conversion = OfferConversion(
            network_id=THEOREMREACH_SLUG,
            external_transaction_id=callback.transaction_id,
            click_id=hashlib.sha256(callback.transaction_id.encode("utf-8")).hexdigest(),
            offer_id="theoremreach",
            external_offer_id=callback.external_transaction_id or callback.transaction_id,
            user_id=user.id,
            provider_payout=callback.payout_usd,
            currency="USD",
            status="APPROVED",
            raw_metadata=json.dumps(
                {
                    "provider": THEOREMREACH_SLUG,
                    "external_transaction_id": callback.external_transaction_id,
                    "reward": callback.reward,
                }
            ),
        )
        db.add(conversion)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            existing = db.scalar(
                select(OfferConversion).where(
                    OfferConversion.network_id == THEOREMREACH_SLUG,
                    OfferConversion.external_transaction_id == callback.transaction_id,
                )
            )
            if existing is None:
                raise HTTPException(503, "TheoremReach conversion could not be recorded.")
            self._validate_existing_conversion(existing, callback)
            if db.scalar(
                select(RewardDecision).where(RewardDecision.conversion_id == existing.id)
            ) is None:
                reward_decision_service.process_conversion(db, existing)
            return

        db.refresh(conversion)
        reward_decision_service.process_conversion(db, conversion)

    def _reverse(
        self,
        db: Session,
        conversion: OfferConversion | None,
        callback: TheoremReachCallback,
    ) -> None:
        if conversion is None:
            raise HTTPException(409, "Original TheoremReach reward was not recorded.")
        self._validate_existing_conversion(conversion, callback)
        if conversion.status == "REVERSED":
            return

        decision = db.scalar(
            select(RewardDecision)
            .where(RewardDecision.conversion_id == conversion.id)
            .with_for_update()
        )
        if decision is None:
            raise HTTPException(503, "Original TheoremReach reward decision is unavailable.")
        if decision.status not in {"APPROVED", "PENDING", "MANUAL_REVIEW"}:
            raise HTTPException(409, "TheoremReach reward cannot be reversed from its current state.")

        reward_decision_service.transition_decision(
            db, decision, "REVERSED", "TheoremReach reported a reward reversal."
        )
        conversion.status = "REVERSED"
        db.commit()

    @staticmethod
    def _validate_existing_conversion(
        conversion: OfferConversion,
        callback: TheoremReachCallback,
    ) -> None:
        if conversion.user_id != callback.user_id:
            raise HTTPException(409, "TheoremReach transaction belongs to another user.")
        if conversion.currency.upper() != "USD":
            raise HTTPException(409, "TheoremReach transaction currency does not match USD.")
        if conversion.provider_payout != callback.payout_usd:
            raise HTTPException(409, "TheoremReach transaction amount does not match its original.")


theoremreach_conversion_service = TheoremReachConversionService()
