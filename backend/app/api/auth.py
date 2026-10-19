import logging
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import current_admin, current_user
from app.core.config import settings
from app.database.session import get_db
from app.models import User
from app.schemas.auth import EmailRequest, LoginRequest, RegisterRequest, ResetPasswordRequest, TokenRequest, UserResponse, VerifyEmailRequest
from app.security.tokens import create_session
from app.services.analytics import record_login_failure
from app.services.auth import authenticate, consume_token, issue_token, issue_verification_code, register, user_response, verify_email_code
from app.services.email import EmailDeliveryError, email_service
from app.services.rate_limit import enforce_cooldown

router = APIRouter(prefix="/auth", tags=["authentication"])
OTP_RESEND_COOLDOWN_SECONDS = 60

def send_verification_code(db: Session, user: User) -> None:
    try:
        email_service.send_verification(user.email, issue_verification_code(db, user))
    except EmailDeliveryError as error:
        db.rollback()
        raise HTTPException(
            503,
            "Verification email could not be delivered. Check the email provider configuration and try again.",
        ) from error
    db.commit()

def check_resend_cooldown(request: Request, email: str) -> None:
    client_host = request.client.host if request.client else "unknown"
    enforce_cooldown(
        f"verify-email:{client_host}:{email.lower()}",
        seconds=OTP_RESEND_COOLDOWN_SECONDS,
        message="Please wait before requesting another verification code.",
    )

def set_session(response: Response, user_id: str, *, admin: bool = False) -> None:
    cookie_name = settings.admin_session_cookie_name if admin else settings.session_cookie_name
    response.set_cookie(cookie_name, create_session(user_id), max_age=settings.session_max_age_seconds, httponly=True, secure=settings.environment == "production", samesite="lax", path="/")

def authenticate_for_login(data: LoginRequest, request: Request, db: Session, login_type: str) -> User:
    try:
        return authenticate(db, str(data.email), data.password)
    except HTTPException as error:
        if error.status_code in {401, 403}:
            record_login_failure(
                db,
                str(data.email),
                login_type,
                request.client.host if request.client else None,
            )
        raise

@router.post("/register", response_model=UserResponse, status_code=201)
def create_account(data: RegisterRequest, db: Session = Depends(get_db)):
    user = register(db, data); logging.info("registration user_id=%s", user.id); return user_response(user)
@router.post("/login", response_model=UserResponse)
def login(data: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    user = authenticate_for_login(data, request, db, "user")
    role_names = {role.name for role in user.roles}
    if "USER" not in role_names or {"ADMIN", "SUPER_ADMIN"}.intersection(role_names):
        record_login_failure(
            db,
            str(data.email),
            "user",
            request.client.host if request.client else None,
        )
        raise HTTPException(403, "This sign-in page is for user accounts.")
    set_session(response, user.id); logging.info("login user_id=%s", user.id); return user_response(user)
@router.post("/admin/login", response_model=UserResponse)
def admin_login(data: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    user = authenticate_for_login(data, request, db, "admin")
    role_names = {role.name for role in user.roles}
    if not {"ADMIN", "SUPER_ADMIN"}.intersection(role_names) or "USER" in role_names:
        record_login_failure(
            db,
            str(data.email),
            "admin",
            request.client.host if request.client else None,
        )
        raise HTTPException(403, "This sign-in page is for administrator accounts.")
    set_session(response, user.id, admin=True); logging.info("admin login user_id=%s", user.id); return user_response(user)
@router.post("/logout", status_code=204)
def logout(response: Response): response.delete_cookie(settings.session_cookie_name, path="/")
@router.post("/admin/logout", status_code=204)
def admin_logout(response: Response): response.delete_cookie(settings.admin_session_cookie_name, path="/")
@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(current_user)): return user_response(user)
@router.get("/admin/me", response_model=UserResponse)
def admin_me(user: User = Depends(current_admin)): return user_response(user)
@router.post("/verify-email")
def verify_email(data: VerifyEmailRequest, db: Session = Depends(get_db)):
    verify_email_code(db, str(data.email), data.code)
    return {"success": True, "message": "Email verified."}

@router.post("/request-verification", status_code=202)
def request_verification(data: EmailRequest, request: Request, db: Session = Depends(get_db)):
    email = str(data.email).lower()
    check_resend_cooldown(request, email)
    user = db.scalar(select(User).where(User.email == email))
    if user and not user.email_verified:
        send_verification_code(db, user)
    return {"success": True, "message": "If the account needs verification, a code has been sent."}

@router.post("/resend-verification", status_code=202)
def resend_verification(
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if not user.email_verified:
        check_resend_cooldown(request, user.email)
        send_verification_code(db, user)
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
