from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import current_user, require_permission
from app.database.session import get_db
from app.models import SupportTicket, SupportTicketMessage, User
from app.schemas.support import (
    AdminSupportTicketRead,
    AdminTicketReply,
    SupportMessageCreate,
    SupportTicketCreate,
    SupportTicketRead,
)
from app.services.rate_limit import enforce_cooldown

router = APIRouter(tags=["support"])


def _ticket_read(ticket: SupportTicket) -> dict:
    return {
        "id": ticket.id,
        "subject": ticket.subject,
        "category": ticket.category,
        "status": ticket.status,
        "created_at": ticket.created_at,
        "updated_at": ticket.updated_at,
        "messages": [
            {
                "id": message.id,
                "sender_role": message.sender_role,
                "body": message.body,
                "created_at": message.created_at,
            }
            for message in ticket.messages
        ],
    }


def _get_ticket(db: Session, ticket_id: str) -> SupportTicket:
    ticket = db.scalar(
        select(SupportTicket)
        .where(SupportTicket.id == ticket_id)
        .options(selectinload(SupportTicket.messages), selectinload(SupportTicket.user))
        .with_for_update()
    )
    if ticket is None:
        raise HTTPException(404, "Support ticket not found.")
    return ticket


@router.get("/support/tickets", response_model=list[SupportTicketRead])
def list_user_tickets(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    tickets = db.scalars(
        select(SupportTicket)
        .where(SupportTicket.user_id == user.id)
        .options(selectinload(SupportTicket.messages))
        .order_by(SupportTicket.updated_at.desc())
        .limit(100)
    ).all()
    return [_ticket_read(ticket) for ticket in tickets]


@router.post("/support/tickets", response_model=SupportTicketRead, status_code=201)
def create_ticket(
    data: SupportTicketCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    enforce_cooldown(f"support-ticket-create:{user.id}", seconds=30)
    ticket = SupportTicket(
        user_id=user.id,
        subject=data.subject,
        category=data.category,
        status="OPEN",
    )
    ticket.messages.append(
        SupportTicketMessage(
            sender_user_id=user.id,
            sender_role="USER",
            body=data.message,
        )
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return _ticket_read(ticket)


@router.post(
    "/support/tickets/{ticket_id}/messages",
    response_model=SupportTicketRead,
)
def reply_to_ticket(
    ticket_id: str,
    data: SupportMessageCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    ticket = _get_ticket(db, ticket_id)
    if ticket.user_id != user.id:
        raise HTTPException(404, "Support ticket not found.")
    if ticket.status == "RESOLVED":
        raise HTTPException(409, "This ticket is resolved. Create a new ticket if you still need help.")
    enforce_cooldown(f"support-ticket-reply:{user.id}", seconds=3)
    ticket.messages.append(
        SupportTicketMessage(
            sender_user_id=user.id,
            sender_role="USER",
            body=data.message,
        )
    )
    ticket.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(ticket)
    return _ticket_read(ticket)


@router.get("/admin/support/tickets", response_model=list[AdminSupportTicketRead])
def list_admin_tickets(
    status: str | None = Query(default=None, pattern="^(OPEN|IN_PROGRESS|RESOLVED)$"),
    _: User = Depends(require_permission("support.manage")),
    db: Session = Depends(get_db),
) -> list[dict]:
    query = select(SupportTicket).options(
        selectinload(SupportTicket.messages), selectinload(SupportTicket.user)
    )
    if status:
        query = query.where(SupportTicket.status == status)
    tickets = db.scalars(
        query.order_by(SupportTicket.updated_at.asc()).limit(200)
    ).all()
    return [
        {
            **_ticket_read(ticket),
            "user_id": ticket.user_id,
            "user_name": ticket.user.full_name,
            "user_email": ticket.user.email,
        }
        for ticket in tickets
    ]


@router.post(
    "/admin/support/tickets/{ticket_id}/reply",
    response_model=AdminSupportTicketRead,
)
def admin_reply_to_ticket(
    ticket_id: str,
    data: AdminTicketReply,
    admin: User = Depends(require_permission("support.manage")),
    db: Session = Depends(get_db),
) -> dict:
    ticket = _get_ticket(db, ticket_id)
    if ticket.status == "RESOLVED":
        raise HTTPException(409, "Resolved tickets cannot receive another reply.")
    ticket.messages.append(
        SupportTicketMessage(
            sender_user_id=admin.id,
            sender_role="ADMIN",
            body=data.message,
        )
    )
    ticket.status = data.status or "IN_PROGRESS"
    ticket.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(ticket)
    return {
        **_ticket_read(ticket),
        "user_id": ticket.user_id,
        "user_name": ticket.user.full_name,
        "user_email": ticket.user.email,
    }
