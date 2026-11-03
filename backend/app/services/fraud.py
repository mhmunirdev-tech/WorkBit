from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import FraudEvent
from app.services.analytics import hash_ip_address, mask_email

FRAUD_EVENT_RETENTION = timedelta(days=90)


@dataclass(frozen=True)
class FraudAssessment:
    score: int = 0
    action: str = "ALLOW"
    risk_level: str = "LOW"
    reasons: tuple[str, ...] = ()


class FraudService:
    """Records explainable risk signals; risk signals never change balances or ban users."""

    def assess_conversion(self, repeated: bool) -> FraudAssessment:
        if repeated:
            return FraudAssessment(
                score=75,
                action="MANUAL_REVIEW",
                risk_level="HIGH",
                reasons=("repeated_conversion",),
            )
        return FraudAssessment()

    def record_registration(
        self,
        db: Session,
        user_id: str,
        ip_address: str | None,
    ) -> FraudEvent:
        now = datetime.now(timezone.utc)
        ip_hash = hash_ip_address(ip_address)
        recent_count = self._recent_count(
            db,
            "REGISTRATION",
            ip_hash,
            now - timedelta(minutes=settings.fraud_registration_window_minutes),
        )
        risk_level = (
            "MEDIUM"
            if recent_count >= settings.fraud_registration_shared_ip_threshold
            else "LOW"
        )
        reason = (
            "Multiple accounts registered from the same IP in a short period."
            if risk_level == "MEDIUM"
            else "Account registration recorded."
        )
        return self._record(
            db,
            user_id=user_id,
            event_type="REGISTRATION",
            risk_level=risk_level,
            reason=reason,
            evidence={
                "prior_registrations_same_ip": recent_count,
                "window_minutes": settings.fraud_registration_window_minutes,
                "shared_ip_alone_is_not_actionable": True,
            },
            ip_hash=ip_hash,
            created_at=now,
        )

    def record_login_failure(
        self,
        db: Session,
        email: str,
        login_type: str,
        ip_address: str | None,
    ) -> FraudEvent:
        now = datetime.now(timezone.utc)
        ip_hash = hash_ip_address(ip_address)
        recent_count = self._recent_count(
            db,
            "LOGIN_FAILURE",
            ip_hash,
            now - timedelta(minutes=settings.fraud_login_window_minutes),
        )
        attempts = recent_count + 1
        risk_level = (
            "HIGH"
            if attempts >= settings.fraud_login_high_attempt_threshold
            else "MEDIUM"
            if attempts >= settings.fraud_login_medium_attempt_threshold
            else "LOW"
        )
        reason = (
            "Repeated failed sign-in attempts from the same IP."
            if risk_level != "LOW"
            else "Failed sign-in recorded."
        )
        return self._record(
            db,
            user_id=None,
            event_type="LOGIN_FAILURE",
            risk_level=risk_level,
            reason=reason,
            evidence={
                "attempts_from_ip": attempts,
                "window_minutes": settings.fraud_login_window_minutes,
                "login_type": login_type,
                "email_masked": mask_email(email),
            },
            ip_hash=ip_hash,
            created_at=now,
        )

    def record_appeal(
        self,
        db: Session,
        user_id: str,
        statement: str,
        ip_address: str | None,
    ) -> FraudEvent:
        event = self._record(
            db,
            user_id=user_id,
            event_type="USER_APPEAL",
            risk_level="LOW",
            reason="Account owner requested a manual review.",
            evidence={"statement": statement.strip()},
            ip_hash=hash_ip_address(ip_address),
            created_at=datetime.now(timezone.utc),
        )
        event.status = "UNDER_REVIEW"
        return event

    @staticmethod
    def _recent_count(
        db: Session,
        event_type: str,
        ip_hash: str | None,
        since: datetime,
    ) -> int:
        if ip_hash is None:
            return 0
        return int(
            db.scalar(
                select(func.count(FraudEvent.id)).where(
                    FraudEvent.event_type == event_type,
                    FraudEvent.ip_hash == ip_hash,
                    FraudEvent.created_at >= since,
                )
            )
            or 0
        )

    @staticmethod
    def _record(
        db: Session,
        *,
        user_id: str | None,
        event_type: str,
        risk_level: str,
        reason: str,
        evidence: dict,
        ip_hash: str | None,
        created_at: datetime,
    ) -> FraudEvent:
        db.execute(
            delete(FraudEvent).where(
                FraudEvent.created_at < created_at - FRAUD_EVENT_RETENTION
            )
        )
        event = FraudEvent(
            user_id=user_id,
            event_type=event_type,
            risk_level=risk_level,
            status="OPEN",
            reason=reason,
            evidence_json=json.dumps(evidence, sort_keys=True),
            ip_hash=ip_hash,
            created_at=created_at,
        )
        db.add(event)
        return event


fraud_service = FraudService()
