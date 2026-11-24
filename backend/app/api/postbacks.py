import ipaddress
import json
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from app.core.config import settings
from app.database.session import get_db
from app.integrations.offer_providers.bitcotasks import (
    BitcoTasksCallbackError,
    BitcoTasksConfigurationError,
    bitcotasks_adapter,
)
from app.integrations.offer_providers.cpx_research import (
    CPXResearchCallbackError,
    CPXResearchConfigurationError,
    cpx_research_adapter,
)
from app.integrations.offer_providers.offerwall_gg import (
    OfferwallGGCallbackError,
    OfferwallGGConfigurationError,
    offerwall_gg_adapter,
)
from app.integrations.offer_providers.offerwall_me import (
    OfferwallMeCallbackError,
    OfferwallMeConfigurationError,
    offerwall_me_adapter,
)
from app.integrations.offer_providers.offerwall_ad import (
    OfferwallAdCallbackError,
    OfferwallAdConfigurationError,
    offerwall_ad_adapter,
)
from app.integrations.offer_providers.moonetix import (
    MoonetixCallbackError,
    MoonetixConfigurationError,
    moonetix_adapter,
)
from app.integrations.offer_providers.theoremreach import (
    TheoremReachCallbackError,
    TheoremReachConfigurationError,
    theoremreach_adapter,
)
from app.schemas.conversions import ConversionRead, MockPostbackRequest
from app.services.conversions import conversion_service
from app.services.cpx_research import cpx_research_conversion_service
from app.services.offerwall_gg import offerwall_gg_conversion_service
from app.services.offerwall_me import offerwall_me_conversion_service
from app.services.offerwall_ad import offerwall_ad_conversion_service
from app.services.moonetix import moonetix_conversion_service
from app.services.theoremreach import theoremreach_conversion_service
from app.services.bitcotasks import bitcotasks_conversion_service
router = APIRouter(prefix="/postbacks", tags=["postbacks"])
OFFERWALL_ME_POSTBACK_SOURCE_IPS = frozenset(
    {"95.216.65.163", "2a01:4f9:2b:1dc::2"}
)
BITCOTASKS_POSTBACK_SOURCE_IPS = frozenset({"45.14.135.48"})
MOONETIX_POSTBACK_SOURCE_IPS = frozenset(
    {"187.124.177.111", "2a02:4780:79:782c::1"}
)


def _is_offerwall_me_source_allowed(request: Request) -> bool:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    source = forwarded_for.split(",", 1)[0].strip()
    try:
        source_ip = ipaddress.ip_address(source)
    except ValueError:
        return False
    return any(
        source_ip == ipaddress.ip_address(value)
        for value in OFFERWALL_ME_POSTBACK_SOURCE_IPS
    )


def _is_bitcotasks_source_allowed(request: Request) -> bool:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    source = forwarded_for.split(",", 1)[0].strip()
    try:
        source_ip = ipaddress.ip_address(source)
    except ValueError:
        return False
    return any(
        source_ip == ipaddress.ip_address(value)
        for value in BITCOTASKS_POSTBACK_SOURCE_IPS
    )


def _is_moonetix_source_allowed(request: Request) -> bool:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    source = forwarded_for.split(",", 1)[0].strip()
    if not source:
        source = request.client.host if request.client else ""
    try:
        source_ip = ipaddress.ip_address(source)
    except ValueError:
        return False
    return any(
        source_ip == ipaddress.ip_address(value)
        for value in MOONETIX_POSTBACK_SOURCE_IPS
    )


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON field: {key}")
        result[key] = value
    return result


@router.post("/mock", response_model=ConversionRead, status_code=202)
def receive_mock_postback(payload: MockPostbackRequest, db: Session = Depends(get_db)):
    if settings.environment != "development":
        raise HTTPException(503, "Provider is not configured.")
    conversion = conversion_service.process_mock(db, payload)
    return ConversionRead(id=conversion.id, external_transaction_id=conversion.external_transaction_id, click_id=conversion.click_id, status=conversion.status, provider_payout=conversion.provider_payout, currency=conversion.currency)


@router.api_route("/moonetix", methods=["GET", "POST"], response_class=PlainTextResponse)
async def receive_moonetix_postback(
    request: Request,
    db: Session = Depends(get_db),
) -> PlainTextResponse:
    if request.method == "GET":
        values = request.query_params
        callback_values = {}
        for key, value in values.multi_items():
            normalized_key = key.lower()
            if normalized_key in callback_values or not isinstance(value, str):
                return PlainTextResponse("FORBIDDEN", status_code=400)
            callback_values[normalized_key] = value
    else:
        content_type = request.headers.get("content-type", "").lower()
        if "application/json" in content_type:
            try:
                payload = await request.json()
            except ValueError:
                return PlainTextResponse("FORBIDDEN", status_code=400)
            if not isinstance(payload, dict):
                return PlainTextResponse("FORBIDDEN", status_code=400)
            callback_values = {
                str(key).lower(): str(value)
                for key, value in payload.items()
                if value is not None
            }
            if len(callback_values) != len(payload):
                return PlainTextResponse("FORBIDDEN", status_code=400)
        else:
            values = await request.form()
            callback_values = {}
            for key, value in values.multi_items():
                normalized_key = key.lower()
                if normalized_key in callback_values or not isinstance(value, str):
                    return PlainTextResponse("FORBIDDEN", status_code=400)
                callback_values[normalized_key] = value

    user_id = (
        callback_values.get("user_id")
        or callback_values.get("userid")
        or callback_values.get("user")
    )
    transaction_id = (
        callback_values.get("transaction_id")
        or callback_values.get("transactionid")
        or callback_values.get("trans_id")
        or callback_values.get("tx_id")
        or callback_values.get("tx")
    )
    test_flag = callback_values.get("test")
    test_status = str(test_flag).lower() if test_flag is not None else ""
    if (
        user_id == "test_user"
        or (user_id is not None and "test" in user_id.lower())
        or (transaction_id is not None and transaction_id.lower().startswith("test"))
        or test_status in {"1", "true", "yes", "test"}
    ):
        return PlainTextResponse("ok")

    if not settings.moonetix_postback_enabled:
        return PlainTextResponse("UNAVAILABLE", status_code=503)
    if not _is_moonetix_source_allowed(request):
        return PlainTextResponse("FORBIDDEN", status_code=403)

    aliases = {
        "transaction_id": transaction_id,
        "user_id": user_id,
        "reward": callback_values.get("reward") or callback_values.get("amount"),
        "payout": callback_values.get("payout") or callback_values.get("payout_usd"),
        "status": callback_values.get("status"),
        "hash": callback_values.get("hash") or callback_values.get("signature"),
        "offer_id": callback_values.get("offer_id") or callback_values.get("offerid"),
        "offer_name": callback_values.get("offer_name") or callback_values.get("offername"),
        "country": callback_values.get("country"),
    }
    callback_values = {key: value for key, value in aliases.items() if value is not None}

    try:
        callback = moonetix_adapter.verify_callback(callback_values)
    except MoonetixConfigurationError:
        return PlainTextResponse("UNAVAILABLE", status_code=503)
    except MoonetixCallbackError:
        return PlainTextResponse("FORBIDDEN", status_code=403)

    try:
        moonetix_conversion_service.process_callback(db, callback)
    except HTTPException as error:
        if error.status_code >= 500:
            return PlainTextResponse("RETRY", status_code=503)
        return PlainTextResponse("REJECTED", status_code=error.status_code)
    return PlainTextResponse("ok")


@router.get("/cpx-research", response_class=PlainTextResponse)
async def receive_cpx_research_postback(
    request: Request,
    db: Session = Depends(get_db),
) -> PlainTextResponse:
    if not settings.cpx_research_postback_enabled:
        return PlainTextResponse("UNAVAILABLE", status_code=503)

    callback_values: dict[str, str] = {}
    for key, value in request.query_params.multi_items():
        normalized_key = key.lower()
        if normalized_key in callback_values:
            return PlainTextResponse("FORBIDDEN", status_code=400)
        callback_values[normalized_key] = value

    try:
        callback = cpx_research_adapter.verify_callback(callback_values)
    except CPXResearchConfigurationError:
        return PlainTextResponse("UNAVAILABLE", status_code=503)
    except CPXResearchCallbackError:
        return PlainTextResponse("FORBIDDEN", status_code=403)

    try:
        cpx_research_conversion_service.process_callback(db, callback)
    except HTTPException as error:
        status_code = error.status_code
        if status_code >= 500:
            return PlainTextResponse("RETRY", status_code=503)
        return PlainTextResponse("REJECTED", status_code=status_code)
    return PlainTextResponse("OK")


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


@router.get("/theoremreach", response_class=PlainTextResponse)
async def receive_theoremreach_postback(
    request: Request,
    db: Session = Depends(get_db),
) -> PlainTextResponse:
    try:
        raw_query = request.scope["query_string"].decode("ascii")
    except UnicodeDecodeError:
        return PlainTextResponse("FORBIDDEN", status_code=400)

    callback_values: dict[str, str] = {}
    for key, value in request.query_params.multi_items():
        normalized_key = key.lower()
        if normalized_key in callback_values:
            return PlainTextResponse("FORBIDDEN", status_code=400)
        callback_values[normalized_key] = value

    try:
        callback = theoremreach_adapter.verify_callback(callback_values, raw_query)
    except TheoremReachConfigurationError:
        return PlainTextResponse("UNAVAILABLE", status_code=503)
    except TheoremReachCallbackError:
        return PlainTextResponse("FORBIDDEN", status_code=403)

    try:
        theoremreach_conversion_service.process_callback(db, callback)
    except HTTPException as error:
        if error.status_code >= 500:
            return PlainTextResponse("RETRY", status_code=503)
        return PlainTextResponse("REJECTED", status_code=error.status_code)
    return PlainTextResponse("OK")


@router.post("/bitcotasks", response_class=PlainTextResponse)
async def receive_bitcotasks_postback(
    request: Request,
    db: Session = Depends(get_db),
) -> PlainTextResponse:
    if not settings.bitcotasks_postback_enabled:
        return PlainTextResponse("UNAVAILABLE", status_code=503)
    if not _is_bitcotasks_source_allowed(request):
        return PlainTextResponse("FORBIDDEN", status_code=403)

    callback_values: dict[str, str] = {}
    form = await request.form()
    for key, value in form.multi_items():
        normalized_key = key.lower()
        if normalized_key in callback_values or not isinstance(value, str):
            return PlainTextResponse("FORBIDDEN", status_code=400)
        callback_values[normalized_key] = value

    try:
        callback = bitcotasks_adapter.verify_callback(callback_values)
    except BitcoTasksConfigurationError:
        return PlainTextResponse("UNAVAILABLE", status_code=503)
    except BitcoTasksCallbackError:
        return PlainTextResponse("FORBIDDEN", status_code=403)

    if callback.debug:
        return PlainTextResponse("ok")

    try:
        bitcotasks_conversion_service.process_callback(db, callback)
    except HTTPException as error:
        if error.status_code >= 500:
            return PlainTextResponse("RETRY", status_code=503)
        return PlainTextResponse("REJECTED", status_code=error.status_code)
    return PlainTextResponse("ok")


@router.post("/offerwall-me", response_class=PlainTextResponse)
async def receive_offerwall_me_postback(
    request: Request,
    db: Session = Depends(get_db),
) -> PlainTextResponse:
    if not settings.offerwall_me_postback_enabled:
        return PlainTextResponse("UNAVAILABLE", status_code=503)
    if not _is_offerwall_me_source_allowed(request):
        return PlainTextResponse("FORBIDDEN", status_code=403)

    form = await request.form()
    callback_values: dict[str, str] = {}
    for key, value in form.multi_items():
        if key in callback_values or not isinstance(value, str):
            return PlainTextResponse("FORBIDDEN", status_code=400)
        callback_values[key] = value

    try:
        callback = offerwall_me_adapter.verify_callback(callback_values)
    except OfferwallMeConfigurationError:
        return PlainTextResponse("UNAVAILABLE", status_code=503)
    except OfferwallMeCallbackError:
        return PlainTextResponse("FORBIDDEN", status_code=403)

    try:
        offerwall_me_conversion_service.process_callback(db, callback)
    except HTTPException as error:
        if error.status_code >= 500:
            return PlainTextResponse("RETRY", status_code=503)
        return PlainTextResponse("REJECTED", status_code=error.status_code)
    return PlainTextResponse("ok")


@router.post("/offerwall-ad", response_class=PlainTextResponse)
async def receive_offerwall_ad_postback(
    request: Request,
    db: Session = Depends(get_db),
) -> PlainTextResponse:
    if not settings.offerwall_ad_postback_enabled:
        return PlainTextResponse("UNAVAILABLE", status_code=503)
    if "application/json" not in request.headers.get("content-type", "").lower():
        return PlainTextResponse("FORBIDDEN", status_code=400)

    raw_body = await request.body()
    try:
        payload = json.loads(
            raw_body.decode("utf-8"),
            parse_float=Decimal,
            parse_int=Decimal,
            object_pairs_hook=_unique_json_object,
        )
    except (UnicodeDecodeError, ValueError):
        return PlainTextResponse("FORBIDDEN", status_code=400)
    if not isinstance(payload, dict):
        return PlainTextResponse("FORBIDDEN", status_code=400)

    try:
        callback = offerwall_ad_adapter.verify_callback(
            payload=payload,
            raw_body=raw_body,
            signature=request.headers.get("x-offerwall-ad-signature", ""),
            signature_source=request.headers.get(
                "x-offerwall-ad-signature-source", ""
            ),
            event_header=request.headers.get("x-offerwall-ad-event", ""),
            event_id=request.headers.get("x-offerwall-ad-event-id", ""),
        )
    except OfferwallAdConfigurationError:
        return PlainTextResponse("UNAVAILABLE", status_code=503)
    except OfferwallAdCallbackError:
        return PlainTextResponse("FORBIDDEN", status_code=403)

    if callback.is_test:
        return PlainTextResponse("OK")

    try:
        offerwall_ad_conversion_service.process_callback(db, callback)
    except HTTPException as error:
        if error.status_code >= 500:
            return PlainTextResponse("RETRY", status_code=503)
        return PlainTextResponse("REJECTED", status_code=error.status_code)
    return PlainTextResponse("OK")


@router.post("/{provider}", status_code=503)
def receive_provider_postback(provider: str):
    raise HTTPException(503, f"Offer provider '{provider}' is not configured.")
