from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Offer, OfferNetwork
from app.schemas.offers import OfferRead


class MockOfferProvider:
    name = "mock"
    async def get_offers(self, db: Session, country: str) -> list[OfferRead]:
        rows = db.execute(
            select(Offer, OfferNetwork.name)
            .join(OfferNetwork, OfferNetwork.id == Offer.network_id)
            .where(
                OfferNetwork.provider == "MOCK",
                OfferNetwork.integration_type == "MOCK",
                OfferNetwork.status == "DEVELOPMENT_ONLY",
                Offer.status == "PUBLISHED",
            )
            .order_by(Offer.priority.desc(), Offer.created_at.desc(), Offer.id)
        ).all()
        return [
            OfferRead(
                id=offer.id,
                title=offer.title,
                short_description=offer.short_description,
                category=offer.category,
                country=country.upper(),
                device_type=offer.device_type,
                user_reward=offer.user_reward,
                currency=offer.currency,
                estimated_time_minutes=offer.estimated_time_minutes,
                difficulty=offer.difficulty,
                featured=offer.featured,
                source_name=source_name,
                is_demo=True,
            )
            for offer, source_name in rows
        ]
