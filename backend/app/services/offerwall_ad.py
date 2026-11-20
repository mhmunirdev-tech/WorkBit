from __future__ import annotations

import hashlib
import json

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.integrations.offer_providers.offerwall_ad import (
    OFFERWALL_AD_SLUG,
    OfferwallAdCallback,
)
from app.models import OfferConversion, RewardDecision, User, Wallet
from app.services.rewards import reward_decision_service

NETWORK_ID = OFFERWALL_AD_SLUG
REWARD_EVENTS = {"conversion.approved", "conversion.released"}


class OfferwallAdConversionService:
    def process_callback(self, db: Session, callback: OfferwallAdCallback) -> None:
        user = db.get(User, callback.user_id)
        if user is None:
            raise HTTPException(400, "Unknown Offerwall Ad visitor.")

        wallet = db.scalar(
            select(Wallet).where(Wallet.user_id == user.id).with_for_update()
        )
        if wallet is None:
            raise HTTPException(409, "User wallet is unavailable.")
        if wallet.currency.upper() != callback.currency:
            raise HTTPException(409, "Offerwall Ad payout currency does not match the wallet.")

        conversion = db.scalar(
            select(OfferConversion)
            .where(
                OfferConversion.network_id == NETWORK_ID,
                OfferConversion.external_transaction_id == callback.transaction_id,
            )
            .with_for_update()
        )
        if conversion is not None:
            self._validate_existing_conversion(conversion, callback)

        if callback.event == "conversion.held":
            self._hold(db, callback, user, conversion)
        elif callback.event in REWARD_EVENTS:
            self._approve(db, callback, user, conversion)
        elif callback.event == "conversion.reversed":
            self._reverse(db, callback, conversion)
        else:
            self._reject(db, callback, conversion)

    def _hold(
        self,
        db: Session,
        callback: OfferwallAdCallback,
        user: User,
        conversion: OfferConversion | None,
    ) -> None:
        if conversion is None:
            conversion = self._new_conversion(callback, user.id, "PENDING")
            db.add(conversion)
            self._commit_new_conversion(db, conversion, callback)
            return
        if conversion.status in {"APPROVED", "REVERSED", "REJECTED"}:
            return
        if db.scalar(
            select(RewardDecision).where(RewardDecision.conversion_id == conversion.id)
        ) is None:
            reward_decision_service.process_conversion(db, conversion)

    def _approve(
        self,
        db: Session,
        callback: OfferwallAdCallback,
        user: User,
        conversion: OfferConversion | None,
    ) -> None:
        if conversion is None:
            conversion = self._new_conversion(callback, user.id, "APPROVED")
            db.add(conversion)
            self._commit_new_conversion(db, conversion, callback)
            return

        decision = db.scalar(
            select(RewardDecision)
            .where(RewardDecision.conversion_id == conversion.id)
            .with_for_update()
        )
        if decision is None:
            conversion.status = "APPROVED"
            reward_decision_service.process_conversion(db, conversion)
            return
        if decision.status == "PENDING":
            conversion.status = "APPROVED"
            reward_decision_service.transition_decision(
                db, decision, "APPROVED", "Offerwall Ad released the held conversion."
            )
        elif decision.status in {"REVERSED", "REJECTED"}:
            return

    def _reverse(
        self,
        db: Session,
        callback: OfferwallAdCallback,
        conversion: OfferConversion | None,
    ) -> None:
        if conversion is None:
            raise HTTPException(409, "Original Offerwall Ad reward was not recorded.")
        if conversion.status == "REVERSED":
            return

        decision = db.scalar(
            select(RewardDecision)
            .where(RewardDecision.conversion_id == conversion.id)
            .with_for_update()
        )
        if decision is None:
            raise HTTPException(503, "Original Offerwall Ad reward decision is unavailable.")
        if decision.status not in {"APPROVED", "PENDING", "MANUAL_REVIEW"}:
            if decision.status == "REJECTED":
                return
            raise HTTPException(409, "Offerwall Ad reward cannot be reversed from its current state.")

        reward_decision_service.transition_decision(
            db, decision, "REVERSED", "Offerwall Ad reported a conversion reversal."
        )
        conversion.status = "REVERSED"
        db.commit()

    def _reject(
        self,
        db: Session,
        callback: OfferwallAdCallback,
        conversion: OfferConversion | None,
    ) -> None:
        if conversion is None or conversion.status in {"REJECTED", "REVERSED"}:
            return
        decision = db.scalar(
            select(RewardDecision)
            .where(RewardDecision.conversion_id == conversion.id)
            .with_for_update()
        )
        if decision is None:
            conversion.status = "REJECTED"
            db.commit()
        elif decision.status in {"PENDING", "MANUAL_REVIEW"}:
            reward_decision_service.transition_decision(
                db, decision, "REJECTED", "Offerwall Ad rejected the conversion."
            )
            conversion.status = "REJECTED"
            db.commit()

    def _commit_new_conversion(
        self,
        db: Session,
        conversion: OfferConversion,
        callback: OfferwallAdCallback,
    ) -> None:
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
                raise HTTPException(503, "Offerwall Ad conversion could not be recorded.")
            self._validate_existing_conversion(existing, callback)
            if db.scalar(
                select(RewardDecision).where(RewardDecision.conversion_id == existing.id)
            ) is None:
                reward_decision_service.process_conversion(db, existing)
            return

        if conversion.status == "APPROVED" or conversion.status == "PENDING":
            reward_decision_service.process_conversion(db, conversion)

    @staticmethod
    def _new_conversion(
        callback: OfferwallAdCallback, user_id: str, status: str
    ) -> OfferConversion:
        return OfferConversion(
            network_id=NETWORK_ID,
            external_transaction_id=callback.transaction_id,
            click_id=hashlib.sha256(callback.transaction_id.encode("utf-8")).hexdigest(),
            offer_id=callback.offer_id or NETWORK_ID,
            external_offer_id=(callback.offer_id or callback.offer_name or callback.transaction_id)[:128],
            user_id=user_id,
            provider_payout=callback.payout,
            currency=callback.currency,
            status=status,
            raw_metadata=json.dumps(
                {
                    "provider": NETWORK_ID,
                    "conversion_id": callback.conversion_id,
                    "offer_name": callback.offer_name,
                    "status": callback.status,
                    "event": callback.event,
                    "event_id": callback.event_id,
                    "network": callback.network,
                    "campaign_id": callback.campaign_id,
                    "click_id": callback.click_id,
                    "unix_timestamp": callback.unix_timestamp,
                }
            ),
        )

    @staticmethod
    def _validate_existing_conversion(
        conversion: OfferConversion,
        callback: OfferwallAdCallback,
    ) -> None:
        if conversion.user_id != callback.user_id:
            raise HTTPException(409, "Offerwall Ad transaction belongs to another visitor.")
        if conversion.currency.upper() != callback.currency:
            raise HTTPException(409, "Offerwall Ad transaction currency does not match.")
        if conversion.provider_payout != callback.payout:
            raise HTTPException(409, "Offerwall Ad transaction payout does not match its original.")


offerwall_ad_conversion_service = OfferwallAdConversionService()
