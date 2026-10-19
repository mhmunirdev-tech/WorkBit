import hashlib
import hmac
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import AnalyticsEvent

ANALYTICS_RETENTION_DAYS = 90
PAGE_VIEW_DEDUPLICATION_SECONDS = 30
VISITOR_PING_DEDUPLICATION_SECONDS = 120


def _digest(kind: str, value: str) -> str:
    return hmac.new(
        settings.session_secret.encode("utf-8"),
        f"{kind}:{value}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def hash_visitor_id(visitor_id: str) -> str:
    return _digest("visitor", visitor_id)


def hash_ip_address(ip_address: str | None) -> str | None:
    return _digest("ip", ip_address) if ip_address else None


def mask_email(email: str) -> str:
    normalized = email.strip().lower()
    local, separator, domain = normalized.partition("@")
    if not separator:
        return f"{normalized[:1]}***"
    return f"{local[:1]}***@{domain}"


def purge_expired_events(db: Session, now: datetime) -> bool:
    cutoff = now - timedelta(days=ANALYTICS_RETENTION_DAYS)
    expired_event = db.scalar(
        select(AnalyticsEvent.id)
        .where(AnalyticsEvent.created_at < cutoff)
        .limit(1)
    )
    if expired_event:
        db.execute(delete(AnalyticsEvent).where(AnalyticsEvent.created_at < cutoff))
        return True
    return False


def record_page_view(
    db: Session,
    visitor_id: str,
    path: str,
    ip_address: str | None,
    event_type: str = "PAGE_VIEW",
) -> None:
    now = datetime.now(timezone.utc)
    visitor_hash = hash_visitor_id(visitor_id)
    deduplication_seconds = (
        VISITOR_PING_DEDUPLICATION_SECONDS
        if event_type == "VISITOR_PING"
        else PAGE_VIEW_DEDUPLICATION_SECONDS
    )
    recent = db.scalar(
        select(AnalyticsEvent.id)
        .where(
            AnalyticsEvent.event_type == event_type,
            AnalyticsEvent.visitor_hash == visitor_hash,
            AnalyticsEvent.path == path,
            AnalyticsEvent.created_at >= now - timedelta(seconds=deduplication_seconds),
        )
        .limit(1)
    )
    if recent:
        return

    purge_expired_events(db, now)
    db.add(
        AnalyticsEvent(
            event_type=event_type,
            visitor_hash=visitor_hash,
            path=path,
            ip_hash=hash_ip_address(ip_address),
            created_at=now,
        )
    )
    db.commit()


def record_login_failure(
    db: Session,
    email: str,
    login_type: str,
    ip_address: str | None,
) -> None:
    now = datetime.now(timezone.utc)
    purge_expired_events(db, now)
    db.add(
        AnalyticsEvent(
            event_type="LOGIN_FAILURE",
            login_type=login_type,
            email_masked=mask_email(email),
            ip_hash=hash_ip_address(ip_address),
            created_at=now,
        )
    )
    db.commit()
