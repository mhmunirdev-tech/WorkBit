from __future__ import annotations

import hashlib
import json

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.integrations.offer_providers.moonetix import (
    MOONETIX_SLUG,
    MoonetixCallback,
)
from app.models import OfferConversion, RewardDecision, User, Wallet
from app.services.rewards import reward_decision_service

NETWORK_ID = MOONETIX_SLUG


class MoonetixConversionService:
    def process_callback(self, db: Session, callback: MoonetixCallback) -> None:
        user = db.get(User, callback.user_id)
        if user is None:
            raise HTTPException(400, "Unknown Moonetix user.")

        wallet = db.scalar(
            select(Wallet).where(Wallet.user_id == user.id).with_for_update()
        )
        if wallet is None:
            raise HTTPException(409, "User wallet is unavailable.")
        if wallet.currency.upper() != "USD":
            raise HTTPException(409, "Moonetix payout does not match the user's USD wallet.")

        conversion = db.scalar(
            select(OfferConversion)
            .where(
                OfferConversion.network_id == NETWORK_ID,
                OfferConversion.external_transaction_id == callback.transaction_id,
            )
            .with_for_update()
        )
        if callback.status == "1":
            self._credit(db, callback, user, conversion)
        else:
            self._reverse(db, callback, conversion)

    def _credit(
        self,
        db: Session,
        callback: MoonetixCallback,
        user: User,
        conversion: OfferConversion | None,
    ) -> None:
        if conversion is not None:
            self._validate_existing_conversion(conversion, callback)
            if db.scalar(
                select(RewardDecision).where(RewardDecision.conversion_id == conversion.id)
            ) is None:
                reward_decision_service.process_conversion(db, conversion)
            return

        conversion = OfferConversion(
            network_id=NETWORK_ID,
            external_transaction_id=callback.transaction_id,
            click_id=hashlib.sha256(callback.transaction_id.encode("utf-8")).hexdigest(),
            offer_id=callback.offer_id,
            external_offer_id=callback.offer_id,
            user_id=user.id,
            provider_payout=callback.amount_usd,
            currency="USD",
            status="APPROVED",
            raw_metadata=json.dumps(
                {
                    "provider": NETWORK_ID,
                    "reward": str(callback.reward),
                    "payout_usd": str(callback.payout_usd),
                    "offer_name": callback.offer_name,
                    "country": callback.country,
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
                    OfferConversion.network_id == NETWORK_ID,
                    OfferConversion.external_transaction_id == callback.transaction_id,
                )
            )
            if existing is None:
                raise HTTPException(503, "Moonetix conversion could not be recorded.")
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
        callback: MoonetixCallback,
        conversion: OfferConversion | None,
    ) -> None:
        if conversion is None:
            raise HTTPException(409, "Original Moonetix reward was not recorded.")
        self._validate_existing_conversion(conversion, callback)
        if conversion.status == "REVERSED":
            return

        decision = db.scalar(
            select(RewardDecision)
            .where(RewardDecision.conversion_id == conversion.id)
            .with_for_update()
        )
        if decision is None:
            raise HTTPException(503, "Original Moonetix reward decision is unavailable.")
        if decision.status not in {"APPROVED", "PENDING", "MANUAL_REVIEW"}:
            raise HTTPException(
                409, "Moonetix reward cannot be reversed from its current state."
            )

        reward_decision_service.transition_decision(
            db, decision, "REVERSED", "Moonetix reported a chargeback or reversal."
        )
        conversion.status = "REVERSED"
        db.commit()

    @staticmethod
    def _validate_existing_conversion(
        conversion: OfferConversion,
        callback: MoonetixCallback,
    ) -> None:
        if conversion.user_id != callback.user_id:
            raise HTTPException(409, "Moonetix transaction belongs to another user.")
        if conversion.currency.upper() != "USD":
            raise HTTPException(409, "Moonetix transaction currency does not match USD.")
        if conversion.provider_payout != callback.amount_usd:
            raise HTTPException(
                409, "Moonetix transaction amount does not match its original."
            )


moonetix_conversion_service = MoonetixConversionService()
