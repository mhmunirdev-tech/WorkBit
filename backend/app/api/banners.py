import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user, require_permission
from app.database.session import get_db
from app.integrations.cloudinary import upload_image
from app.models import DashboardBanner, User
from app.schemas.banners import DashboardBannerCreate, DashboardBannerRead

router = APIRouter(tags=["dashboard banners"])
MAX_BANNER_SIZE = 5 * 1024 * 1024
IMAGE_SIGNATURES = {
    "image/jpeg": lambda data: data.startswith(b"\xff\xd8\xff"),
    "image/png": lambda data: data.startswith(b"\x89PNG\r\n\x1a\n"),
    "image/webp": lambda data: data.startswith(b"RIFF") and data[8:12] == b"WEBP",
}


@router.get("/dashboard/banners", response_model=list[DashboardBannerRead])
def list_active_banners(
    _user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[DashboardBanner]:
    return list(
        db.scalars(
            select(DashboardBanner)
            .where(DashboardBanner.is_active.is_(True))
            .order_by(DashboardBanner.sort_order, DashboardBanner.created_at.desc())
        ).all()
    )


@router.get("/admin/dashboard-banners", response_model=list[DashboardBannerRead])
def list_admin_banners(
    _admin: User = Depends(require_permission("settings.manage")),
    db: Session = Depends(get_db),
) -> list[DashboardBanner]:
    return list(
        db.scalars(
            select(DashboardBanner).order_by(
                DashboardBanner.sort_order, DashboardBanner.created_at.desc()
            )
        ).all()
    )


@router.post("/admin/dashboard-banners/upload-image")
def upload_banner_image(
    file: UploadFile = File(...),
    _admin: User = Depends(require_permission("settings.manage")),
) -> dict[str, str]:
    signature_check = IMAGE_SIGNATURES.get(file.content_type or "")
    if signature_check is None:
        raise HTTPException(415, "Choose a JPEG, PNG, or WebP image.")

    image = file.file.read(MAX_BANNER_SIZE + 1)
    if len(image) > MAX_BANNER_SIZE:
        raise HTTPException(413, "Banner images must be 5 MB or smaller.")
    if not signature_check(image):
        raise HTTPException(415, "The uploaded file is not a valid supported image.")

    image_url = upload_image(
        image,
        file.content_type or "",
        f"workbit/banners/{uuid.uuid4()}",
    )
    return {"image_url": image_url}


@router.post(
    "/admin/dashboard-banners",
    response_model=DashboardBannerRead,
    status_code=status.HTTP_201_CREATED,
)
def create_banner(
    banner_data: DashboardBannerCreate,
    _admin: User = Depends(require_permission("settings.manage")),
    db: Session = Depends(get_db),
) -> DashboardBanner:
    banner = DashboardBanner(**banner_data.model_dump())
    db.add(banner)
    db.commit()
    db.refresh(banner)
    return banner


@router.post("/admin/dashboard-banners/{banner_id}", response_model=DashboardBannerRead)
def update_banner(
    banner_id: str,
    banner_data: DashboardBannerCreate,
    _admin: User = Depends(require_permission("settings.manage")),
    db: Session = Depends(get_db),
) -> DashboardBanner:
    banner = db.get(DashboardBanner, banner_id)
    if banner is None:
        raise HTTPException(404, "Banner not found.")
    for field, value in banner_data.model_dump().items():
        setattr(banner, field, value)
    db.commit()
    db.refresh(banner)
    return banner


@router.post("/admin/dashboard-banners/{banner_id}/delete", status_code=status.HTTP_204_NO_CONTENT)
def delete_banner(
    banner_id: str,
    _admin: User = Depends(require_permission("settings.manage")),
    db: Session = Depends(get_db),
) -> None:
    banner = db.get(DashboardBanner, banner_id)
    if banner is None:
        raise HTTPException(404, "Banner not found.")
    db.delete(banner)
    db.commit()
