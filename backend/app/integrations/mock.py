from decimal import Decimal
from app.integrations.base import OfferProvider
from app.schemas.offers import OfferRead
class MockOfferProvider(OfferProvider):
    name = "mock"
    async def get_offers(self, country: str) -> list[OfferRead]:
        return [OfferRead(id="mock-game", title="Install Demo Game", short_description="A development-only example offer.", category="GAME", country=country, device_type="MOBILE", user_reward=Decimal("0.50"), currency="USD", estimated_time_minutes=20, difficulty="Medium", featured=True), OfferRead(id="mock-survey", title="Complete Demo Survey", short_description="A development-only feedback survey.", category="SURVEY", country=country, device_type="WEB", user_reward=Decimal("0.25"), currency="USD", estimated_time_minutes=8, difficulty="Easy", featured=False), OfferRead(id="mock-signup", title="Create Demo Account", short_description="A development-only registration example.", category="SIGNUP", country=country, device_type="WEB", user_reward=Decimal("0.75"), currency="USD", estimated_time_minutes=5, difficulty="Easy", featured=True)]
    async def redirect_url(self, offer_id: str, click_id: str, sub_id: str) -> str:
        raise NotImplementedError("Mock offers do not redirect to external providers.")
