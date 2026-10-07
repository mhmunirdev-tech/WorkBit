import logging
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models import AuthToken, Profile, Role, User, Wallet
from app.security.passwords import hash_password, verify_password
from app.security.tokens import generate_token, token_hash
from app.services.email import EmailDeliveryError, email_service

def user_response(user: User) -> dict:
    return {"id": user.id, "email": user.email, "full_name": user.full_name, "country": user.country, "status": user.status, "email_verified": user.email_verified, "roles": [role.name for role in user.roles]}
def referral_code() -> str: return "WB" + uuid4().hex[:8].upper()
def issue_token(db: Session, user: User, purpose: str) -> str:
    raw = generate_token()
    db.add(AuthToken(user_id=user.id, purpose=purpose, token_hash=token_hash(raw), expires_at=datetime.now(timezone.utc)+timedelta(minutes=settings.token_ttl_minutes)))
    return raw
def register(db: Session, data) -> User:
    if db.scalar(select(User).where(User.email == str(data.email).lower())): raise HTTPException(400, "An account with this email already exists.")
    referrer = db.scalar(select(User).where(User.referral_code == data.referral_code.upper())) if data.referral_code else None
    if data.referral_code and not referrer: raise HTTPException(400, "The referral code is invalid.")
    role = db.scalar(select(Role).where(Role.name == "USER"))
    if not role:
        logging.error("registration is unavailable because the USER role has not been seeded")
        raise HTTPException(
            503,
            "Registration is unavailable because required roles are missing. "
            "Run the seed command against the configured database.",
        )
    user = User(email=str(data.email).lower(), password_hash=hash_password(data.password), full_name=data.full_name.strip(), country=data.country, referral_code=referral_code(), referred_by=referrer.id if referrer else None)
    user.roles.append(role); user.profile = Profile(); user.wallet = Wallet(); db.add(user); db.flush()
    try:
        email_service.send_verification(user.email, issue_token(db, user, "VERIFY_EMAIL"))
    except EmailDeliveryError as error:
        db.rollback()
        raise HTTPException(
            503,
            "Account creation is temporarily unavailable because verification email "
            "could not be delivered. Check the email provider configuration and try again.",
        ) from error
    db.commit(); db.refresh(user); return user
def authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email.lower()))
    if not user or not verify_password(password, user.password_hash): raise HTTPException(401, "Invalid email or password.")
    if user.status in {"SUSPENDED", "BANNED"}: raise HTTPException(403, "This account is unavailable.")
    return user
def consume_token(db: Session, raw: str, purpose: str) -> User:
    record = db.scalar(select(AuthToken).where(AuthToken.token_hash == token_hash(raw), AuthToken.purpose == purpose, AuthToken.used_at.is_(None)))
    if not record:
        raise HTTPException(400, "The token is invalid or expired.")
    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(400, "The token is invalid or expired.")
    user = db.get(User, record.user_id)
    if not user: raise HTTPException(400, "The token is invalid or expired.")
    record.used_at = datetime.now(timezone.utc); return user
