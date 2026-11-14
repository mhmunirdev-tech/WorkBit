from __future__ import annotations

import hashlib
import json

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.integrations.offer_providers.bitcotasks import (
    BITCOTASKS_SLUG,
    BitcoTasksCallback,
)
from app.models import OfferConversion, RewardDecision, User, Wallet
from app.services.rewards import reward_decision_service

NETWORK_ID = BITCOTASKS_SLUG


class BitcoTasksConversionService:
    def process_callback(self, db: Session, callback: BitcoTasksCallback) -> None:
        user = db.get(User, callback.user_id)
        if user is None:
            raise HTTPException(400, "Unknown BitcoTasks user.")

        wallet = db.scalar(
            select(Wallet).where(Wallet.user_id == user.id).with_for_update()
        )
        if wallet is None:
            raise HTTPException(409, "User wallet is unavailable.")
        if wallet.currency.upper() != "USD":
            raise HTTPException(409, "BitcoTasks payout does not match the user's USD wallet.")

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
            return
        self._reverse(db, callback, conversion)

    def _credit(
        self,
        db: Session,
        callback: BitcoTasksCallback,
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
            offer_id=callback.offer_type or NETWORK_ID,
            external_offer_id=(callback.offer_name or callback.transaction_id)[:128],
            user_id=user.id,
            provider_payout=callback.amount_usd,
            currency="USD",
            status="APPROVED",
            raw_metadata=json.dumps(
                {
                    "provider": NETWORK_ID,
                    "offer_name": callback.offer_name,
                    "offer_type": callback.offer_type,
                    "reward": callback.reward,
                    "reward_value": str(callback.reward_value),
                    "provider_reported_payout_usd": str(
                        callback.reported_payout_usd
                    ),
                    "reward_name": callback.reward_name,
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
                raise HTTPException(503, "BitcoTasks conversion could not be recorded.")
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
        callback: BitcoTasksCallback,
        conversion: OfferConversion | None,
    ) -> None:
        if conversion is None:
            raise HTTPException(409, "Original BitcoTasks reward was not recorded.")
        self._validate_existing_conversion(conversion, callback)
        if conversion.status == "REVERSED":
            return

        decision = db.scalar(
            select(RewardDecision)
            .where(RewardDecision.conversion_id == conversion.id)
            .with_for_update()
        )
        if decision is None:
            raise HTTPException(503, "Original BitcoTasks reward decision is unavailable.")
        if decision.status not in {"APPROVED", "PENDING", "MANUAL_REVIEW"}:
            raise HTTPException(
                409, "BitcoTasks reward cannot be reversed from its current state."
            )

        reward_decision_service.transition_decision(
            db, decision, "REVERSED", "BitcoTasks reported a chargeback or reversal."
        )
        conversion.status = "REVERSED"
        db.commit()

    @staticmethod
    def _validate_existing_conversion(
        conversion: OfferConversion,
        callback: BitcoTasksCallback,
    ) -> None:
        if conversion.user_id != callback.user_id:
            raise HTTPException(409, "BitcoTasks transaction belongs to another user.")
        if conversion.currency.upper() != "USD":
            raise HTTPException(409, "BitcoTasks transaction currency does not match USD.")
        if conversion.provider_payout != callback.amount_usd:
            raise HTTPException(
                409, "BitcoTasks transaction amount does not match its original."
            )


bitcotasks_conversion_service = BitcoTasksConversionService()
