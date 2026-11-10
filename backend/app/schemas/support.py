from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


TicketCategory = Literal["OFFER_REWARD", "WITHDRAWAL", "ACCOUNT", "OTHER"]
TicketStatus = Literal["OPEN", "IN_PROGRESS", "RESOLVED"]


class SupportTicketCreate(BaseModel):
    subject: str = Field(min_length=5, max_length=120)
    category: TicketCategory
    message: str = Field(min_length=10, max_length=4000)

    @field_validator("subject", "message")
    @classmethod
    def trim_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("This field cannot be blank.")
        return normalized


class SupportMessageCreate(BaseModel):
    message: str = Field(min_length=1, max_length=4000)

    @field_validator("message")
    @classmethod
    def trim_message(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Message cannot be blank.")
        return normalized


class AdminTicketReply(SupportMessageCreate):
    status: TicketStatus | None = None


class SupportMessageRead(BaseModel):
    id: str
    sender_role: Literal["USER", "ADMIN"]
    body: str
    created_at: datetime


class SupportTicketRead(BaseModel):
    id: str
    subject: str
    category: TicketCategory
    status: TicketStatus
    created_at: datetime
    updated_at: datetime
    messages: list[SupportMessageRead]


class AdminSupportTicketRead(SupportTicketRead):
    user_id: str
    user_name: str
    user_email: str
