from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from app.core.config import settings
from app.database.session import get_db
from app.integrations.offer_providers.offerwall_gg import (
    OfferwallGGCallbackError,
    OfferwallGGConfigurationError,
    offerwall_gg_adapter,
)
from app.schemas.conversions import ConversionRead, MockPostbackRequest
from app.services.conversions import conversion_service
from app.services.offerwall_gg import offerwall_gg_conversion_service
router = APIRouter(prefix="/postbacks", tags=["postbacks"])


@router.post("/mock", response_model=ConversionRead, status_code=202)
def receive_mock_postback(payload: MockPostbackRequest, db: Session = Depends(get_db)):
    if settings.environment != "development":
        raise HTTPException(503, "Provider is not configured.")
    conversion = conversion_service.process_mock(db, payload)
    return ConversionRead(id=conversion.id, external_transaction_id=conversion.external_transaction_id, click_id=conversion.click_id, status=conversion.status, provider_payout=conversion.provider_payout, currency=conversion.currency)


@router.api_route("/offerwall-gg", methods=["GET", "POST"], response_class=PlainTextResponse)
async def receive_offerwall_gg_postback(
    request: Request,
    db: Session = Depends(get_db),
) -> PlainTextResponse:
    if request.method == "GET":
        values = request.query_params
    else:
        values = await request.form()

    field_names = (
        "userId",
        "transactionId",
        "offerId",
        "offerName",
        "goalId",
        "currencyAmount",
        "currencyName",
        "status",
        "test",
        "timestamp",
        "signature",
    )
    callback_values: dict[str, str] = {}
    for field_name in field_names:
        supplied_values = values.getlist(field_name)
        if len(supplied_values) > 1 or any(not isinstance(value, str) for value in supplied_values):
            return PlainTextResponse("FORBIDDEN", status_code=400)
        if supplied_values:
            callback_values[field_name] = supplied_values[0]

    try:
        callback = offerwall_gg_adapter.verify_callback(callback_values)
    except OfferwallGGConfigurationError:
        return PlainTextResponse("UNAVAILABLE", status_code=503)
    except OfferwallGGCallbackError:
        return PlainTextResponse("FORBIDDEN", status_code=403)

    if callback.test:
        return PlainTextResponse("OK")

    try:
        offerwall_gg_conversion_service.process_callback(db, callback)
    except HTTPException as error:
        status_code = error.status_code
        if status_code >= 500:
            return PlainTextResponse("RETRY", status_code=503)
        return PlainTextResponse("REJECTED", status_code=status_code)
    return PlainTextResponse("OK")


@router.post("/{provider}", status_code=503)
def receive_provider_postback(provider: str):
    raise HTTPException(503, f"Offer provider '{provider}' is not configured.")
