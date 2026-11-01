from __future__ import annotations

import hashlib
import json

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.integrations.offer_providers.cpx_research import (
    CPXResearchCallback,
)
from app.models import OfferConversion, RewardDecision, User, Wallet
from app.services.rewards import reward_decision_service

CPX_RESEARCH_SLUG = "cpx-research"


class CPXResearchConversionService:
    def process_callback(self, db: Session, callback: CPXResearchCallback) -> None:
        if callback.amount_usd == 0:
            return

        user = db.get(User, callback.user_id)
        if user is None:
            raise HTTPException(400, "Unknown CPX Research user.")
        wallet = db.scalar(
            select(Wallet).where(Wallet.user_id == user.id).with_for_update()
        )
        if wallet is None:
            raise HTTPException(409, "User wallet is unavailable.")
        if wallet.currency.upper() != "USD":
            raise HTTPException(409, "CPX Research USD payout does not match the user's wallet.")

        conversion = db.scalar(
            select(OfferConversion)
            .where(
                OfferConversion.network_id == CPX_RESEARCH_SLUG,
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
        callback: CPXResearchCallback,
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
            network_id=CPX_RESEARCH_SLUG,
            external_transaction_id=callback.transaction_id,
            click_id=hashlib.sha256(callback.transaction_id.encode("utf-8")).hexdigest(),
            offer_id=callback.offer_id or "cpx-research",
            external_offer_id=callback.offer_id or callback.transaction_id,
            user_id=user.id,
            provider_payout=callback.amount_usd,
            currency="USD",
            status="APPROVED",
            raw_metadata=json.dumps(
                {
                    "provider": CPX_RESEARCH_SLUG,
                    "event_type": callback.event_type,
                    "amount_local": callback.amount_local,
                    "sub_id_1": callback.sub_id_1,
                    "sub_id_2": callback.sub_id_2,
                    "ip_click": callback.ip_click,
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
                    OfferConversion.network_id == CPX_RESEARCH_SLUG,
                    OfferConversion.external_transaction_id == callback.transaction_id,
                )
            )
            if existing is None:
                raise HTTPException(503, "CPX Research conversion could not be recorded.")
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
        callback: CPXResearchCallback,
        conversion: OfferConversion | None,
    ) -> None:
        if conversion is None:
            raise HTTPException(409, "Original CPX Research reward was not recorded.")
        self._validate_existing_conversion(conversion, callback)
        if conversion.status == "REVERSED":
            return

        decision = db.scalar(
            select(RewardDecision)
            .where(RewardDecision.conversion_id == conversion.id)
            .with_for_update()
        )
        if decision is None:
            raise HTTPException(503, "Original CPX Research reward decision is unavailable.")
        if decision.status not in {"APPROVED", "PENDING", "MANUAL_REVIEW"}:
            raise HTTPException(409, "CPX Research reward cannot be reversed from its current state.")

        reward_decision_service.transition_decision(
            db, decision, "REVERSED", "CPX Research reported a canceled or fraudulent event."
        )
        conversion.status = "REVERSED"
        db.commit()

    @staticmethod
    def _validate_existing_conversion(
        conversion: OfferConversion,
        callback: CPXResearchCallback,
    ) -> None:
        if conversion.user_id != callback.user_id:
            raise HTTPException(409, "CPX Research transaction belongs to another user.")
        if conversion.currency.upper() != "USD":
            raise HTTPException(409, "CPX Research transaction currency does not match USD.")
        if conversion.provider_payout != callback.amount_usd:
            raise HTTPException(409, "CPX Research transaction amount does not match its original.")


cpx_research_conversion_service = CPXResearchConversionService()
