from __future__ import annotations

import hashlib
import json
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.integrations.offer_providers.offerwall_gg import OfferwallGGCallback
from app.models import OfferConversion, RewardDecision, User, Wallet
from app.services.rewards import reward_decision_service

NETWORK_ID = "offerwall-gg"


class OfferwallGGConversionService:
    def process_callback(self, db: Session, callback: OfferwallGGCallback) -> OfferConversion:
        user = db.get(User, callback.user_id)
        if user is None:
            raise HTTPException(400, "Unknown Offerwall.GG user.")

        wallet = db.scalar(
            select(Wallet).where(Wallet.user_id == user.id).with_for_update()
        )
        if wallet is None:
            raise HTTPException(409, "User wallet is unavailable.")
        if wallet.currency.upper() != callback.currency:
            raise HTTPException(409, "Callback currency does not match the user's wallet.")

        conversion = db.scalar(
            select(OfferConversion)
            .where(
                OfferConversion.network_id == NETWORK_ID,
                OfferConversion.external_transaction_id == callback.transaction_id,
            )
            .with_for_update()
        )

        if callback.status == "credited":
            conversion = self._credit(db, callback, user, conversion)
            decision = db.scalar(
                select(RewardDecision).where(RewardDecision.conversion_id == conversion.id)
            )
            if decision is None:
                reward_decision_service.process_conversion(db, conversion)
            return conversion

        if conversion is None:
            raise HTTPException(409, "Original conversion is not recorded yet.")
        self._validate_existing_conversion(conversion, callback)
        if conversion.status == "REVERSED":
            return conversion

        decision = db.scalar(
            select(RewardDecision)
            .where(RewardDecision.conversion_id == conversion.id)
            .with_for_update()
        )
        if decision is None:
            reward_decision_service.process_conversion(db, conversion)
            db.refresh(conversion)
            decision = db.scalar(
                select(RewardDecision)
                .where(RewardDecision.conversion_id == conversion.id)
                .with_for_update()
            )
        if decision is None:
            raise HTTPException(503, "Conversion reward could not be recorded.")

        conversion.status = "REVERSED"
        reward_decision_service.transition_decision(
            db, decision, "REVERSED", "Offerwall.GG reported a signed reversal."
        )
        return conversion

    def _credit(
        self,
        db: Session,
        callback: OfferwallGGCallback,
        user: User,
        conversion: OfferConversion | None,
    ) -> OfferConversion:
        if conversion is not None:
            self._validate_existing_conversion(conversion, callback)
            return conversion

        transaction_fingerprint = hashlib.sha256(
            callback.transaction_id.encode("utf-8")
        ).hexdigest()
        conversion = OfferConversion(
            network_id=NETWORK_ID,
            external_transaction_id=callback.transaction_id,
            click_id=transaction_fingerprint,
            offer_id=callback.offer_id or "offerwall-gg",
            external_offer_id=callback.offer_id or callback.transaction_id,
            user_id=user.id,
            provider_payout=callback.amount,
            currency=callback.currency,
            status="APPROVED",
            raw_metadata=json.dumps({
                "provider": NETWORK_ID,
                "offer_name": callback.offer_name,
                "goal_id": callback.goal_id,
                "callback_timestamp": callback.timestamp,
            }),
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
                raise HTTPException(503, "Conversion could not be durably recorded.")
            self._validate_existing_conversion(existing, callback)
            return existing
        db.refresh(conversion)
        return conversion

    def _validate_existing_conversion(
        self, conversion: OfferConversion, callback: OfferwallGGCallback
    ) -> None:
        expected_amount = (
            callback.amount
            if callback.status == "credited"
            else -callback.amount
        )
        if conversion.user_id != callback.user_id:
            raise HTTPException(409, "Transaction is already linked to another user.")
        if conversion.currency.upper() != callback.currency:
            raise HTTPException(409, "Transaction currency does not match its original conversion.")
        if conversion.provider_payout != expected_amount:
            raise HTTPException(409, "Callback amount does not match the original conversion.")


offerwall_gg_conversion_service = OfferwallGGConversionService()
