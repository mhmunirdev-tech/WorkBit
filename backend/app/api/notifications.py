from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.database.session import get_db
from app.models import RewardNotification, User
from app.schemas.notifications import RewardNotificationListRead, RewardNotificationRead

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=RewardNotificationListRead)
def list_notifications(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> RewardNotificationListRead:
    items = db.scalars(
        select(RewardNotification)
        .where(RewardNotification.user_id == user.id)
        .order_by(RewardNotification.created_at.desc())
        .limit(30)
    ).all()
    unread_count = db.scalar(
        select(func.count(RewardNotification.id)).where(
            RewardNotification.user_id == user.id,
            RewardNotification.read_at.is_(None),
        )
    ) or 0
    return RewardNotificationListRead(items=items, unread_count=unread_count)


@router.post("/{notification_id}/read", response_model=RewardNotificationRead)
def mark_notification_read(
    notification_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> RewardNotificationRead:
    notification = db.scalar(
        select(RewardNotification).where(
            RewardNotification.id == notification_id,
            RewardNotification.user_id == user.id,
        )
    )
    if notification is None:
        raise HTTPException(404, "Notification not found.")
    if notification.read_at is None:
        notification.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(notification)
    return RewardNotificationRead.model_validate(notification)
