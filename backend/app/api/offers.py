from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from app.api.deps import current_user
from app.database.session import get_db
from app.models import User
from app.schemas.offers import OfferRead
from app.services.offers import offer_service
router = APIRouter(prefix="/offers", tags=["offers"])
@router.get("", response_model=list[OfferRead])
async def list_offers(country: str = Query("US", min_length=2, max_length=2), category: str | None = None, device: str | None = None, offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)) -> list[OfferRead]:
    return await offer_service.list(country.upper(), category, device, offset, limit)
@router.get("/{offer_id}", response_model=OfferRead)
async def offer_detail(offer_id: str, country: str = Query("US", min_length=2, max_length=2)) -> OfferRead:
    return await offer_service.detail(offer_id, country.upper())
@router.post("/{offer_id}/click", status_code=202)
async def offer_click(offer_id: str, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict[str, str]:
    return await offer_service.track_click(db, user, offer_id, request.client.host if request.client else None, request.headers.get("user-agent"))
@router.post("/{offer_id}/redirect")
async def offer_redirect(offer_id: str, user: User = Depends(current_user)) -> None:
    await offer_service.redirect(user, offer_id)
