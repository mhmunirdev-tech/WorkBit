from __future__ import annotations

import hashlib
import json

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.integrations.offer_providers.bitlabs import BITLABS_SLUG, BitLabsCallback
from app.models import OfferConversion, RewardDecision, User, Wallet
from app.services.rewards import reward_decision_service


class BitLabsConversionService:
    def process_callback(self, db: Session, callback: BitLabsCallback) -> None:
        if callback.debug:
            return
        if callback.activity_type == "COMPLETE":
            if callback.offer_state in {"PENDING", "RECONCILED"}:
                return
            if callback.payout_usd <= 0:
                return
            self._credit(db, callback)
            return
        if callback.activity_type == "RECONCILIATION":
            self._reconcile(db, callback)

    def _credit(self, db: Session, callback: BitLabsCallback) -> None:
        user = db.get(User, callback.user_id)
        if user is None:
            raise HTTPException(400, "Unknown BitLabs user.")
        wallet = db.scalar(
            select(Wallet).where(Wallet.user_id == user.id).with_for_update()
        )
        if wallet is None:
            raise HTTPException(409, "User wallet is unavailable.")
        if wallet.currency.upper() != "USD":
            raise HTTPException(409, "BitLabs USD payout does not match the user's wallet.")

        conversion = db.scalar(
            select(OfferConversion)
            .where(
                OfferConversion.network_id == BITLABS_SLUG,
                OfferConversion.external_transaction_id == callback.transaction_id,
            )
            .with_for_update()
        )
        if conversion is not None:
            self._validate_existing_conversion(conversion, callback)
            if db.scalar(
                select(RewardDecision).where(RewardDecision.conversion_id == conversion.id)
            ) is None:
                reward_decision_service.process_conversion(db, conversion)
            return

        conversion = OfferConversion(
            network_id=BITLABS_SLUG,
            external_transaction_id=callback.transaction_id,
            click_id=hashlib.sha256(callback.transaction_id.encode("utf-8")).hexdigest(),
            offer_id=callback.offer_id or "bitlabs",
            external_offer_id=callback.task_id or callback.offer_id or callback.transaction_id,
            user_id=user.id,
            provider_payout=callback.payout_usd,
            currency="USD",
            status="APPROVED",
            raw_metadata=json.dumps(
                {
                    "provider": BITLABS_SLUG,
                    "activity_type": callback.activity_type,
                    "offer_id": callback.offer_id,
                    "task_id": callback.task_id,
                    "offer_state": callback.offer_state,
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
                    OfferConversion.network_id == BITLABS_SLUG,
                    OfferConversion.external_transaction_id == callback.transaction_id,
                )
            )
            if existing is None:
                raise HTTPException(503, "BitLabs conversion could not be recorded.")
            self._validate_existing_conversion(existing, callback)
            if db.scalar(
                select(RewardDecision).where(RewardDecision.conversion_id == existing.id)
            ) is None:
                reward_decision_service.process_conversion(db, existing)
            return

        db.refresh(conversion)
        reward_decision_service.process_conversion(db, conversion)

    def _reconcile(self, db: Session, callback: BitLabsCallback) -> None:
        original_transaction_id = callback.reference_id or callback.transaction_id
        conversion = db.scalar(
            select(OfferConversion)
            .where(
                OfferConversion.network_id == BITLABS_SLUG,
                OfferConversion.external_transaction_id == original_transaction_id,
            )
            .with_for_update()
        )
        if conversion is None:
            return
        if conversion.user_id != callback.user_id:
            raise HTTPException(409, "BitLabs reconciliation user does not match the original.")
        if conversion.status == "REVERSED":
            return
        if (
            callback.payout_usd != 0
            and abs(callback.payout_usd) != conversion.provider_payout
        ):
            raise HTTPException(
                503,
                "BitLabs reported a partial reconciliation that requires manual review.",
            )

        decision = db.scalar(
            select(RewardDecision)
            .where(RewardDecision.conversion_id == conversion.id)
            .with_for_update()
        )
        if decision is None:
            decision = reward_decision_service.process_conversion(db, conversion)
        if decision.status in {"APPROVED", "PENDING", "MANUAL_REVIEW"}:
            reward_decision_service.transition_decision(
                db, decision, "REVERSED", "BitLabs reported a reconciliation."
            )
        conversion.status = "REVERSED"
        db.commit()

    @staticmethod
    def _validate_existing_conversion(
        conversion: OfferConversion, callback: BitLabsCallback
    ) -> None:
        if conversion.user_id != callback.user_id:
            raise HTTPException(409, "BitLabs transaction is linked to another user.")
        if conversion.currency.upper() != "USD":
            raise HTTPException(409, "BitLabs transaction currency does not match USD.")
        if conversion.provider_payout != callback.payout_usd:
            raise HTTPException(409, "BitLabs transaction amount does not match its original.")


bitlabs_conversion_service = BitLabsConversionService()
