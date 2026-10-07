from datetime import datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, Field
ConversionStatus = Literal["PENDING", "APPROVED", "REJECTED", "REVERSED", "CHARGEBACK", "FRAUD", "MANUAL_REVIEW"]
class MockPostbackRequest(BaseModel):
    transaction_id: str = Field(min_length=1, max_length=128)
    click_id: str = Field(min_length=16, max_length=64)
    offer_id: str = Field(min_length=1, max_length=128)
    payout: Decimal = Field(gt=0, max_digits=18, decimal_places=8)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    status: ConversionStatus = "PENDING"
    occurred_at: datetime | None = None
class ConversionRead(BaseModel):
    id: str; external_transaction_id: str; click_id: str; status: str; provider_payout: Decimal; currency: str
