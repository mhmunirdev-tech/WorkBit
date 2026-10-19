from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.database.session import get_db
from app.models import AnalyticsEvent, User
from app.schemas.analytics import AdminAnalyticsRead, PageViewCreate
from app.services.analytics import purge_expired_events, record_page_view

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post("/page-view", status_code=202)
def track_page_view(
    data: PageViewCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    record_page_view(
        db,
        str(data.visitor_id),
        data.path,
        request.client.host if request.client else None,
        data.event_type,
    )
    return {"status": "recorded"}


@router.get("/admin", response_model=AdminAnalyticsRead)
def admin_analytics(
    _: User = Depends(require_permission("users.view")),
    db: Session = Depends(get_db),
) -> AdminAnalyticsRead:
    now = datetime.now(timezone.utc)
    today = now.date()
    if purge_expired_events(db, now):
        db.commit()
    today_start = datetime.combine(today, time.min, timezone.utc)
    active_cutoff = now - timedelta(minutes=5)
    failed_cutoff = now - timedelta(hours=24)
    trend_cutoff = today_start - timedelta(days=89)

    active_visitors = db.scalar(
        select(func.count(distinct(AnalyticsEvent.visitor_hash))).where(
            AnalyticsEvent.event_type.in_(("PAGE_VIEW", "VISITOR_PING")),
            AnalyticsEvent.visitor_hash.is_not(None),
            AnalyticsEvent.created_at >= active_cutoff,
        )
    ) or 0
    unique_visitors_today = db.scalar(
        select(func.count(distinct(AnalyticsEvent.visitor_hash))).where(
            AnalyticsEvent.event_type == "PAGE_VIEW",
            AnalyticsEvent.visitor_hash.is_not(None),
            AnalyticsEvent.created_at >= today_start,
        )
    ) or 0
    page_views_today = db.scalar(
        select(func.count(AnalyticsEvent.id)).where(
            AnalyticsEvent.event_type == "PAGE_VIEW",
            AnalyticsEvent.created_at >= today_start,
        )
    ) or 0
    failed_logins_24h = db.scalar(
        select(func.count(AnalyticsEvent.id)).where(
            AnalyticsEvent.event_type == "LOGIN_FAILURE",
            AnalyticsEvent.created_at >= failed_cutoff,
        )
    ) or 0

    recent_events = db.scalars(
        select(AnalyticsEvent)
        .where(
            AnalyticsEvent.event_type == "LOGIN_FAILURE",
            AnalyticsEvent.created_at >= failed_cutoff,
        )
        .order_by(AnalyticsEvent.created_at.desc())
        .limit(20)
    ).all()

    daily_visitors: dict[date, tuple[int, int]] = {}
    for event_date, visitors, page_views in db.execute(
        select(
            func.date(AnalyticsEvent.created_at),
            func.count(distinct(AnalyticsEvent.visitor_hash)),
            func.count(AnalyticsEvent.id),
        )
        .where(
            AnalyticsEvent.event_type == "PAGE_VIEW",
            AnalyticsEvent.created_at >= trend_cutoff,
        )
        .group_by(func.date(AnalyticsEvent.created_at))
    ):
        parsed_date = event_date if isinstance(event_date, date) else date.fromisoformat(str(event_date))
        daily_visitors[parsed_date] = (visitors, page_views)

    daily_failures: dict[date, int] = {}
    for event_date, failure_count in db.execute(
        select(
            func.date(AnalyticsEvent.created_at),
            func.count(AnalyticsEvent.id),
        )
        .where(
            AnalyticsEvent.event_type == "LOGIN_FAILURE",
            AnalyticsEvent.created_at >= trend_cutoff,
        )
        .group_by(func.date(AnalyticsEvent.created_at))
    ):
        parsed_date = event_date if isinstance(event_date, date) else date.fromisoformat(str(event_date))
        daily_failures[parsed_date] = failure_count

    daily = [
        {
            "date": (today - timedelta(days=offset)),
            "unique_visitors": daily_visitors.get(today - timedelta(days=offset), (0, 0))[0],
            "page_views": daily_visitors.get(today - timedelta(days=offset), (0, 0))[1],
            "failed_logins": daily_failures.get(today - timedelta(days=offset), 0),
        }
        for offset in reversed(range(90))
    ]

    return AdminAnalyticsRead(
        active_visitors=active_visitors,
        unique_visitors_today=unique_visitors_today,
        page_views_today=page_views_today,
        failed_logins_24h=failed_logins_24h,
        recent_failed_logins=[
            {
                "login_type": event.login_type,
                "email_masked": event.email_masked,
                "ip_fingerprint": event.ip_hash[:12] if event.ip_hash else None,
                "created_at": event.created_at,
            }
            for event in recent_events
        ],
        daily=daily,
    )
