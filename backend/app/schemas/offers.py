from decimal import Decimal
from pydantic import BaseModel

class OfferRead(BaseModel):
    id: str; title: str; short_description: str; category: str; country: str; device_type: str
    user_reward: Decimal; currency: str; estimated_time_minutes: int; difficulty: str; featured: bool; is_demo: bool = True
