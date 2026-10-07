import json, logging
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.core.config import settings
from app.models import OfferClick, OfferConversion, RewardDecision, User
from app.schemas.conversions import MockPostbackRequest
from app.services.fraud import fraud_service
from app.services.rewards import reward_decision_service

TERMINAL = {"REJECTED", "REVERSED", "CHARGEBACK", "FRAUD"}
class ConversionService:
    def process_mock(self, db: Session, data: MockPostbackRequest) -> OfferConversion:
        click = db.scalar(select(OfferClick).where(OfferClick.click_id == data.click_id))
        if not click: raise HTTPException(400, "Unknown click identifier.")
        if click.offer_id != data.offer_id: raise HTTPException(400, "Offer does not match click identifier.")
        user = db.get(User, click.user_id)
        if not user: raise HTTPException(400, "Click user is unavailable.")
        existing = db.scalar(select(OfferConversion).where(OfferConversion.network_id == "mock", OfferConversion.external_transaction_id == data.transaction_id))
        if existing:
            if existing.click_id != data.click_id: raise HTTPException(409, "Transaction identifier conflict.")
            if data.status in {"REVERSED", "CHARGEBACK", "REJECTED", "FRAUD"} and existing.status not in TERMINAL:
                existing.status = data.status
                db.commit(); db.refresh(existing)
                decision = db.scalar(select(RewardDecision).where(RewardDecision.conversion_id == existing.id))
                if decision:
                    reward_decision_service.transition_decision(db, decision, data.status, f"Provider reported {data.status.lower()}.")
                logging.info("conversion transitioned transaction=%s status=%s", data.transaction_id, data.status)
                return existing
            if settings.environment == "development" and settings.enable_mock_rewards:
                reward_decision_service.process_conversion(db, existing)
            raise HTTPException(409, "Duplicate conversion received.")
        assessment = fraud_service.assess_conversion(False)
        status = "MANUAL_REVIEW" if assessment.action == "MANUAL_REVIEW" else data.status
        conversion = OfferConversion(network_id="mock", external_transaction_id=data.transaction_id, click_id=click.click_id, offer_id=click.offer_id, external_offer_id=click.external_offer_id, user_id=user.id, provider_payout=data.payout, currency=data.currency.upper(), status=status, raw_metadata=json.dumps({"source":"mock", "fraud_score":assessment.score}), occurred_at=data.occurred_at or click.created_at)
        db.add(conversion)
        try: db.commit()
        except IntegrityError:
            db.rollback(); raise HTTPException(409, "Duplicate conversion received.")
        db.refresh(conversion)
        if settings.environment == "development" and settings.enable_mock_rewards:
            reward_decision_service.process_conversion(db, conversion)
        logging.info("conversion created transaction=%s status=%s", data.transaction_id, status); return conversion
conversion_service = ConversionService()
