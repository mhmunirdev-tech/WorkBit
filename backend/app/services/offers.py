from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.core.config import settings
from app.integrations.mock import MockOfferProvider
from app.models import OfferClick
from app.schemas.offers import OfferRead
from app.services.rate_limit import enforce_cooldown
from app.models import User
from uuid import uuid4

class OfferService:
    """Core catalog logic remains independent of external provider formats."""
    async def list(self, country: str, category: str | None, device: str | None, offset: int, limit: int) -> list[OfferRead]:
        if settings.environment != "development": raise HTTPException(503, "No approved offer provider is configured.")
        offers = await MockOfferProvider().get_offers(country)
        offers = [item for item in offers if (not category or item.category == category.upper()) and (not device or item.device_type == device.upper())]
        return sorted(offers, key=lambda item: (not item.featured, -item.user_reward))[offset:offset + limit]
    async def detail(self, offer_id: str, country: str) -> OfferRead:
        offer = next((item for item in await self.list(country, None, None, 0, 100) if item.id == offer_id), None)
        if not offer: raise HTTPException(404, "Offer not found or unavailable in your country.")
        return offer
    async def track_click(self, db: Session, user: User, offer_id: str, ip_address: str | None, user_agent: str | None) -> dict[str, str]:
        offer = await self.detail(offer_id, user.country)
        enforce_cooldown(f"offer-click:{user.id}:{offer.id}")
        click_id, sub_id = uuid4().hex, uuid4().hex
        db.add(OfferClick(user_id=user.id, offer_id=offer.id, network_id="mock", external_offer_id=offer.id, click_id=click_id, sub_id=sub_id, ip_address=ip_address, user_agent=(user_agent or "")[:512] or None, device_type=offer.device_type)); db.commit()
        return {"click_id": click_id, "status": "recorded", "message": "Development offer click recorded. No reward is created."}
    async def redirect(self, user: User, offer_id: str) -> None:
        await self.detail(offer_id, user.country)
        raise HTTPException(503, "This provider is not configured for redirects.")

offer_service = OfferService()
