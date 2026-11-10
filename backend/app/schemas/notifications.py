from datetime import datetime

from pydantic import BaseModel


class RewardNotificationRead(BaseModel):
    id: str
    reward_decision_id: str
    status: str
    title: str
    message: str
    reason: str | None
    read_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RewardNotificationListRead(BaseModel):
    items: list[RewardNotificationRead]
    unread_count: int
