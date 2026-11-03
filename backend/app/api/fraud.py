import json
from datetime import datetime, time, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.database.session import get_db
from app.models import AdminLog, FraudEvent, Role, User
from app.schemas.fraud import (
    FraudAccountAction,
    FraudAppealCodeRequest,
    FraudAppealSubmit,
    FraudEventRead,
    FraudEventReview,
    FraudOverviewRead,
)
from app.services.analytics import hash_ip_address
from app.services.auth import consume_action_code, issue_action_code
from app.services.email import EmailDeliveryError, email_service
from app.services.fraud import fraud_service
from app.services.rate_limit import enforce_cooldown

router = APIRouter(prefix="/admin/fraud", tags=["admin fraud"])
appeals_router = APIRouter(prefix="/fraud/appeals", tags=["fraud appeals"])


@router.get("/overview", response_model=FraudOverviewRead)
def fraud_overview(
    _: User = Depends(require_permission("users.view")),
    db: Session = Depends(get_db),
) -> FraudOverviewRead:
    today = datetime.combine(datetime.now(timezone.utc).date(), time.min, timezone.utc)

    def count(*conditions) -> int:
        return int(
            db.scalar(
                select(func.count(FraudEvent.id)).where(*conditions)
            )
            or 0
        )

    return FraudOverviewRead(
        open_medium=count(
            FraudEvent.status == "OPEN",
            FraudEvent.risk_level == "MEDIUM",
        ),
        open_high=count(
            FraudEvent.status == "OPEN",
            FraudEvent.risk_level == "HIGH",
        ),
        under_review=count(FraudEvent.status == "UNDER_REVIEW"),
        confirmed=count(FraudEvent.status == "CONFIRMED"),
        events_today=count(FraudEvent.created_at >= today),
    )


@router.get("/events", response_model=list[FraudEventRead])
def list_fraud_events(
    status: str | None = Query(default=None, pattern="^(OPEN|UNDER_REVIEW|CLEARED|CONFIRMED)$"),
    risk_level: str | None = Query(default=None, pattern="^(LOW|MEDIUM|HIGH)$"),
    page: int = Query(default=1, ge=1, le=100000),
    page_size: int = Query(default=50, ge=1, le=100),
    _: User = Depends(require_permission("users.view")),
    db: Session = Depends(get_db),
) -> list[FraudEventRead]:
    query = (
        select(FraudEvent, User.email)
        .outerjoin(User, User.id == FraudEvent.user_id)
        .order_by(FraudEvent.created_at.desc(), FraudEvent.id.desc())
    )
    if status:
        query = query.where(FraudEvent.status == status)
    if risk_level:
        query = query.where(FraudEvent.risk_level == risk_level)
    else:
        query = query.where(
            or_(
                FraudEvent.risk_level.in_(("MEDIUM", "HIGH")),
                FraudEvent.status == "UNDER_REVIEW",
            )
        )

    rows = db.execute(query.offset((page - 1) * page_size).limit(page_size)).all()
    return [
        FraudEventRead(
            id=event.id,
            user_id=event.user_id,
            user_email=email,
            event_type=event.event_type,
            risk_level=event.risk_level,
            status=event.status,
            reason=event.reason,
            evidence=json.loads(event.evidence_json),
            ip_fingerprint=event.ip_hash[:12] if event.ip_hash else None,
            review_note=event.review_note,
            reviewed_at=event.reviewed_at,
            created_at=event.created_at,
        )
        for event, email in rows
    ]


@router.patch("/events/{event_id}", response_model=FraudEventRead)
def review_fraud_event(
    event_id: str,
    data: FraudEventReview,
    request: Request,
    admin: User = Depends(require_permission("users.suspend")),
    db: Session = Depends(get_db),
) -> FraudEventRead:
    event = db.get(FraudEvent, event_id)
    if event is None:
        raise HTTPException(404, "Fraud event not found.")
    if event.status in {"CLEARED", "CONFIRMED"} and data.status != event.status:
        raise HTTPException(409, "A completed fraud review cannot be changed.")

    event.status = data.status
    event.reviewed_by = admin.id
    event.review_note = data.note.strip()
    event.reviewed_at = datetime.now(timezone.utc)
    db.add(
        AdminLog(
            admin_id=admin.id,
            action="FRAUD_EVENT_REVIEWED",
            target_type="fraud_event",
            target_id=event.id,
            metadata_json=json.dumps(
                {"status": event.status, "note": event.review_note}
            ),
            ip_address=None,
            user_agent=request.headers.get("user-agent", "")[:512] or None,
        )
    )
    db.commit()
    db.refresh(event)
    user_email = db.scalar(select(User.email).where(User.id == event.user_id))
    return FraudEventRead(
        id=event.id,
        user_id=event.user_id,
        user_email=user_email,
        event_type=event.event_type,
        risk_level=event.risk_level,
        status=event.status,
        reason=event.reason,
        evidence=json.loads(event.evidence_json),
        ip_fingerprint=event.ip_hash[:12] if event.ip_hash else None,
        review_note=event.review_note,
        reviewed_at=event.reviewed_at,
        created_at=event.created_at,
    )


@router.post("/users/{user_id}/status")
def update_fraud_account_status(
    user_id: str,
    data: FraudAccountAction,
    request: Request,
    admin: User = Depends(require_permission("users.suspend")),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    user = db.scalar(
        select(User)
        .where(User.id == user_id, User.roles.any(Role.name == "USER"))
        .with_for_update()
    )
    if user is None:
        raise HTTPException(404, "User account not found.")
    if data.status == "ACTIVE" and not user.email_verified:
        raise HTTPException(409, "An unverified account cannot be restored as active.")

    previous_status = user.status
    user.status = data.status
    admin_log = AdminLog(
        admin_id=admin.id,
        action="FRAUD_ACCOUNT_STATUS_CHANGED",
        target_type="user",
        target_id=user.id,
        metadata_json=json.dumps(
            {
                "previous_status": previous_status,
                "status": user.status,
                "reason": data.reason.strip(),
                "ip_fingerprint": hash_ip_address(
                    request.client.host if request.client else None
                ),
            }
        ),
        ip_address=None,
        user_agent=request.headers.get("user-agent", "")[:512] or None,
    )
    db.add(admin_log)
    db.commit()
    return {"user_id": user.id, "status": user.status}


@appeals_router.post("/request-code", status_code=202)
def request_fraud_appeal_code(
    data: FraudAppealCodeRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    email = str(data.email).lower()
    enforce_cooldown(
        f"fraud-appeal:{request.client.host if request.client else 'unknown'}:{email}",
        seconds=60,
        message="Please wait before requesting another appeal code.",
    )
    user = db.scalar(select(User).where(User.email == email))
    if user and user.status in {
        "PENDING_REVIEW",
        "SUSPENDED",
        "BANNED",
    }:
        code = issue_action_code(db, user, "FRAUD_APPEAL", user.id)
        try:
            email_service.send_security_code(user.email, code, "account appeal")
        except EmailDeliveryError as error:
            db.rollback()
            raise HTTPException(
                503,
                "The appeal verification email could not be delivered. Try again later.",
            ) from error
        db.commit()
    return {
        "message": "If the account is eligible to appeal, a verification code has been sent."
    }


@appeals_router.post("", status_code=202)
def submit_fraud_appeal(
    data: FraudAppealSubmit,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    user = db.scalar(select(User).where(User.email == str(data.email).lower()))
    if user is None or user.status not in {"PENDING_REVIEW", "SUSPENDED", "BANNED"}:
        raise HTTPException(400, "The appeal code is invalid or expired.")

    consume_action_code(db, user, "FRAUD_APPEAL", user.id, data.code)
    pending_appeal = db.scalar(
        select(FraudEvent.id).where(
            FraudEvent.user_id == user.id,
            FraudEvent.event_type == "USER_APPEAL",
            FraudEvent.status.in_(("OPEN", "UNDER_REVIEW")),
        )
    )
    if pending_appeal:
        db.commit()
        raise HTTPException(409, "An account appeal is already under review.")

    fraud_service.record_appeal(
        db,
        user.id,
        data.statement,
        request.client.host if request.client else None,
    )
    db.commit()
    return {"message": "Your appeal has been submitted for manual review."}
