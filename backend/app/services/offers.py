from fastapi import HTTPException
from sqlalchemy.orm import Session
from decimal import Decimal
from app.core.config import settings
from app.integrations.mock import MockOfferProvider
from app.models import OfferClick
from app.schemas.offers import OfferRead
from app.services.rate_limit import enforce_cooldown
from app.models import User
from uuid import uuid4

class OfferService:
    """Core catalog logic remains independent of external provider formats."""
    async def list(
        self,
        db: Session,
        country: str,
        category: str | None,
        device: str | None,
        offset: int,
        limit: int,
        minimum_reward: Decimal | None = None,
        maximum_time: int | None = None,
    ) -> list[OfferRead]:
        if settings.environment != "development": raise HTTPException(503, "No approved offer provider is configured.")
        offers = await MockOfferProvider().get_offers(db, country)
        offers = [item for item in offers if (not category or item.category == category.upper()) and (not device or item.device_type == device.upper())]
        if minimum_reward is not None:
            offers = [
                item for item in offers
                if item.estimated_user_reward is not None
                and item.estimated_user_reward >= minimum_reward
            ]
        if maximum_time is not None:
            offers = [
                item for item in offers
                if item.estimated_time_minutes <= maximum_time
            ]
        return sorted(offers, key=lambda item: (not item.featured, -item.user_reward))[offset:offset + limit]
    async def detail(self, db: Session, offer_id: str, country: str) -> OfferRead:
        offer = next((item for item in await self.list(db, country, None, None, 0, 100) if item.id == offer_id), None)
        if not offer: raise HTTPException(404, "Offer not found or unavailable in your country.")
        return offer
    async def track_click(
        self,
        db: Session,
        user: User,
        offer_id: str,
        ip_address: str | None,
        user_agent: str | None,
        cooldown_scope: str = "click",
    ) -> dict[str, str]:
        offer = await self.detail(db, offer_id, user.country)
        enforce_cooldown(f"offer-{cooldown_scope}:{user.id}:{offer.id}")
        click_id, sub_id = uuid4().hex, uuid4().hex
        db.add(OfferClick(user_id=user.id, offer_id=offer.id, network_id="mock", external_offer_id=offer.id, click_id=click_id, sub_id=sub_id, ip_address=ip_address, user_agent=(user_agent or "")[:512] or None, device_type=offer.device_type)); db.commit()
        return {"click_id": click_id, "status": "recorded", "message": "Development offer click recorded. No reward is created."}
    async def redirect(self, db: Session, user: User, offer_id: str) -> None:
        await self.detail(db, offer_id, user.country)
        raise HTTPException(503, "This provider is not configured for redirects.")

offer_service = OfferService()
