from abc import ABC, abstractmethod
from app.schemas.offers import OfferRead
class OfferProvider(ABC):
    """Contract for integrations built only from verified publisher documentation."""
    name: str
    @abstractmethod
    async def get_offers(self, country: str) -> list[OfferRead]: ...
    async def redirect_url(self, offer_id: str, click_id: str, sub_id: str) -> str:
        """Implement only from a provider's verified publisher specification."""
        raise NotImplementedError
