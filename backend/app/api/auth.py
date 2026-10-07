import logging
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import current_user
from app.core.config import settings
from app.database.session import get_db
from app.models import User
from app.schemas.auth import EmailRequest, LoginRequest, RegisterRequest, ResetPasswordRequest, TokenRequest, UserResponse
from app.security.tokens import create_session
from app.services.auth import authenticate, consume_token, issue_token, register, user_response
from app.services.email import EmailDeliveryError, email_service

router = APIRouter(prefix="/auth", tags=["authentication"])
def set_session(response: Response, user_id: str) -> None:
    response.set_cookie(settings.session_cookie_name, create_session(user_id), max_age=settings.session_max_age_seconds, httponly=True, secure=settings.environment == "production", samesite="lax", path="/")

@router.post("/register", response_model=UserResponse, status_code=201)
def create_account(data: RegisterRequest, db: Session = Depends(get_db)):
    user = register(db, data); logging.info("registration user_id=%s", user.id); return user_response(user)
@router.post("/login", response_model=UserResponse)
def login(data: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = authenticate(db, str(data.email), data.password); set_session(response, user.id); logging.info("login user_id=%s", user.id); return user_response(user)
@router.post("/logout", status_code=204)
def logout(response: Response): response.delete_cookie(settings.session_cookie_name, path="/")
@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(current_user)): return user_response(user)
@router.post("/verify-email")
def verify_email(data: TokenRequest, db: Session = Depends(get_db)):
    user = consume_token(db, data.token, "VERIFY_EMAIL")
    user.email_verified = True
    if user.status == "PENDING_VERIFICATION":
        user.status = "ACTIVE"
    db.commit()
    return {"success": True, "message": "Email verified."}
@router.post("/resend-verification", status_code=202)
def resend_verification(user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not user.email_verified:
        try:
            email_service.send_verification(user.email, issue_token(db, user, "VERIFY_EMAIL"))
        except EmailDeliveryError as error:
            db.rollback()
            raise HTTPException(
                503,
                "Verification email could not be delivered. Check the email provider configuration and try again.",
            ) from error
        db.commit()
    return {"success": True, "message": "If needed, a verification email has been sent."}
@router.post("/forgot-password", status_code=202)
def forgot_password(data: EmailRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == str(data.email).lower()))
    if user: email_service.send_password_reset(user.email, issue_token(db, user, "RESET_PASSWORD")); db.commit()
    return {"success": True, "message": "If the account exists, a password reset email has been sent."}
@router.post("/reset-password")
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    from app.security.passwords import hash_password
    user = consume_token(db, data.token, "RESET_PASSWORD"); user.password_hash = hash_password(data.password); db.commit()
    return {"success": True, "message": "Password updated."}
