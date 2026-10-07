from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.config import settings
from app.database.session import get_db
from app.schemas.conversions import ConversionRead, MockPostbackRequest
from app.services.conversions import conversion_service
router = APIRouter(prefix="/postbacks", tags=["postbacks"])


@router.post("/mock", response_model=ConversionRead, status_code=202)
def receive_mock_postback(payload: MockPostbackRequest, db: Session = Depends(get_db)):
    if settings.environment != "development":
        raise HTTPException(503, "Provider is not configured.")
    conversion = conversion_service.process_mock(db, payload)
    return ConversionRead(id=conversion.id, external_transaction_id=conversion.external_transaction_id, click_id=conversion.click_id, status=conversion.status, provider_payout=conversion.provider_payout, currency=conversion.currency)


@router.post("/{provider}", status_code=503)
def receive_provider_postback(provider: str):
    raise HTTPException(503, f"Offer provider '{provider}' is not configured.")
