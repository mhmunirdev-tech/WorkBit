import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.database.session import get_db
from app.integrations.cloudinary import upload_image
from app.models import Profile, User
from app.schemas.auth import AccountUpdateRequest, UserResponse
from app.security.passwords import hash_password, verify_password
from app.services.auth import user_response

router = APIRouter(tags=["profile"])
MAX_AVATAR_SIZE = 5 * 1024 * 1024
AVATAR_SIGNATURES = {
    "image/jpeg": lambda data: data.startswith(b"\xff\xd8\xff"),
    "image/png": lambda data: data.startswith(b"\x89PNG\r\n\x1a\n"),
    "image/webp": lambda data: data.startswith(b"RIFF") and data[8:12] == b"WEBP",
}

@router.patch("/profile/account", response_model=UserResponse)
def update_account(
    data: AccountUpdateRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    if data.new_password is not None:
        if data.current_password is None or not verify_password(data.current_password, user.password_hash):
            raise HTTPException(400, "Current password is incorrect.")
        user.password_hash = hash_password(data.new_password)
    if data.full_name is not None:
        user.full_name = data.full_name
    db.commit()
    db.refresh(user)
    return user_response(user)


@router.post("/profile/avatar")
def upload_profile_avatar(
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    signature_check = AVATAR_SIGNATURES.get(file.content_type or "")
    if signature_check is None:
        raise HTTPException(415, "Choose a JPEG, PNG, or WebP image.")

    image = file.file.read(MAX_AVATAR_SIZE + 1)
    if len(image) > MAX_AVATAR_SIZE:
        raise HTTPException(413, "Profile photos must be 5 MB or smaller.")
    if not signature_check(image):
        raise HTTPException(415, "The uploaded file is not a valid supported image.")

    try:
        avatar_url = upload_image(image, file.content_type or "", f"workbit/avatars/{user.id}")
    except HTTPException as error:
        if error.status_code == 503:
            raise HTTPException(503, "Profile photo uploads are not configured.") from error
        if error.status_code == 502:
            logging.error("Cloudinary avatar upload failed user_id=%s", user.id)
            raise HTTPException(502, "Profile photo upload failed. Please try again.") from error
        raise
    profile = user.profile
    if profile is None:
        profile = Profile(user_id=user.id)
        db.add(profile)
    profile.avatar_url = avatar_url
    db.commit()
    return {"avatar_url": avatar_url}
