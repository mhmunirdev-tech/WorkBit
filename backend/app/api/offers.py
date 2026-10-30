from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.config import settings
from app.database.session import get_db
from app.integrations.offer_providers.offerwall_gg import (
    OfferwallGGConfigurationError,
    offerwall_gg_adapter,
)
from app.integrations.offer_providers.bitlabs import (
    BitLabsConfigurationError,
    bitlabs_adapter,
)
from app.models import Offer, RewardDecision, User, Wallet
from app.schemas.offerwall_gg import OfferwallGGOffersRead
from app.schemas.conversions import MockPostbackRequest
from app.schemas.offers import OfferRead
from app.services.conversions import conversion_service
from app.services.offers import offer_service
from app.services.offerwall_gg_catalog import offerwall_gg_catalog_service
from app.services.packages import has_active_package

router = APIRouter(prefix="/offers", tags=["offers"])


@router.get(
    "/providers/offerwall-gg/catalog",
    response_model=OfferwallGGOffersRead,
    response_model_exclude_none=False,
)
async def offerwall_gg_catalog(
    request: Request,
    response: Response,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    search: str | None = Query(None, max_length=80),
    category: str | None = Query(None, min_length=1, max_length=40),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> OfferwallGGOffersRead:
    if not has_active_package(db, user.id):
        raise HTTPException(402, "Buy a package and wait for admin approval before earning from ads.")

    user_agent = request.headers.get("user-agent", "").lower()
    if "android" in user_agent:
        device = "android"
    elif "iphone" in user_agent or "ipad" in user_agent:
        device = "ios"
    elif "mobile" in user_agent:
        device = "mobile"
    else:
        device = "desktop"

    result = await offerwall_gg_catalog_service.list_offers(
        db=db,
        user=user,
        device=device,
        page=page,
        limit=limit,
        search=search.strip() if search else None,
        category=category.strip().lower() if category else None,
    )
    response.headers["Cache-Control"] = "no-store"
    return result


@router.get("/providers/bitlabs/wall-url")
def bitlabs_wall_url(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    if not settings.bitlabs_enabled:
        raise HTTPException(404, "BitLabs is not enabled.")
    if not has_active_package(db, user.id):
        raise HTTPException(402, "Buy a package and wait for admin approval before earning from ads.")
    try:
        wall_url = bitlabs_adapter.build_wall_url(user.id)
    except BitLabsConfigurationError as error:
        raise HTTPException(503, str(error)) from error
    return JSONResponse({"wall_url": wall_url}, headers={"Cache-Control": "no-store"})


@router.get("/providers/offerwall-gg/wall-url")
def offerwall_gg_wall_url(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    if not has_active_package(db, user.id):
        raise HTTPException(402, "Buy a package and wait for admin approval before earning from ads.")
    try:
        wall_url = offerwall_gg_adapter.build_wall_url(user.id)
    except OfferwallGGConfigurationError as error:
        raise HTTPException(503, str(error)) from error
    return JSONResponse({"wall_url": wall_url}, headers={"Cache-Control": "no-store"})


@router.get("", response_model=list[OfferRead])
async def list_offers(country: str = Query("US", min_length=2, max_length=2), category: str | None = None, device: str | None = None, offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)) -> list[OfferRead]:
    return await offer_service.list(db, country.upper(), category, device, offset, limit)


@router.get("/{offer_id}", response_model=OfferRead)
async def offer_detail(offer_id: str, country: str = Query("US", min_length=2, max_length=2), db: Session = Depends(get_db)) -> OfferRead:
    return await offer_service.detail(db, offer_id, country.upper())


@router.post("/{offer_id}/click", status_code=202)
async def offer_click(offer_id: str, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict[str, str]:
    return await offer_service.track_click(db, user, offer_id, request.client.host if request.client else None, request.headers.get("user-agent"))


@router.post("/{offer_id}/simulate-completion")
async def simulate_offer_completion(
    offer_id: str,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    if settings.environment != "development" or not settings.enable_mock_rewards:
        raise HTTPException(
            503,
            "Ad completion simulation is available only in development when ENABLE_MOCK_REWARDS=true.",
        )

    click = await offer_service.track_click(
        db,
        user,
        offer_id,
        request.client.host if request.client else None,
        request.headers.get("user-agent"),
        cooldown_scope="simulation",
    )
    wallet = db.scalar(select(Wallet).where(Wallet.user_id == user.id))
    if wallet is None:
        raise HTTPException(409, "Wallet is unavailable for this conversion.")
    offer = db.get(Offer, offer_id)
    if offer is None:
        raise HTTPException(404, "Offer not found or unavailable.")

    conversion = conversion_service.process_mock(
        db,
        MockPostbackRequest(
            transaction_id=f"test-ad-{uuid4().hex}",
            click_id=click["click_id"],
            offer_id=offer_id,
            payout=offer.user_reward,
            currency=wallet.currency,
            status="APPROVED",
        ),
    )
    decision = db.scalar(
        select(RewardDecision).where(RewardDecision.conversion_id == conversion.id)
    )
    if decision is None:
        raise HTTPException(503, "The simulated conversion did not create a reward decision.")

    db.refresh(wallet)
    if decision.status == "PENDING":
        message = (
            f"Test ad completed. {decision.user_reward} {decision.currency} was added to "
            "your pending balance. Admin approval moves it to your available balance."
        )
    elif decision.status == "MANUAL_REVIEW":
        message = "Test ad completed. The reward is waiting for manual review."
    elif decision.status == "APPROVED":
        message = (
            f"Test ad completed. {decision.user_reward} {decision.currency} was added to "
            f"your available balance; {decision.platform_share} {decision.currency} was "
            "retained as the platform share."
        )
    else:
        message = f"Test ad completed, but the reward was not approved ({decision.status.lower()})."

    return {
        "conversion_id": conversion.id,
        "reward_status": decision.status,
        "reward_amount": str(decision.user_reward),
        "platform_share_amount": str(decision.platform_share),
        "currency": decision.currency,
        "available_balance": str(wallet.available_balance),
        "pending_balance": str(wallet.pending_balance),
        "message": message,
    }


@router.post("/{offer_id}/redirect")
async def offer_redirect(offer_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> None:
    await offer_service.redirect(db, user, offer_id)
