import hashlib
import logging
import time

import httpx
from fastapi import HTTPException

from app.core.config import settings


def _upload_media(
    media: bytes,
    content_type: str,
    public_id: str,
    resource_type: str,
    media_label: str,
) -> str:
    cloud_name = settings.cloudinary_cloud_name
    api_key = settings.cloudinary_api_key
    api_secret = settings.cloudinary_api_secret
    if not cloud_name or not api_key or not api_secret:
        raise HTTPException(503, "Image uploads are not configured.")

    params = {
        "invalidate": "true",
        "overwrite": "true",
        "public_id": public_id,
        "timestamp": str(int(time.time())),
    }
    signed_params = "&".join(f"{key}={value}" for key, value in sorted(params.items()))
    signature = hashlib.sha1(f"{signed_params}{api_secret}".encode("utf-8")).hexdigest()
    try:
        response = httpx.post(
            f"https://api.cloudinary.com/v1_1/{cloud_name}/{resource_type}/upload",
            data={**params, "api_key": api_key, "signature": signature},
            files={"file": (media_label, media, content_type)},
            timeout=20,
        )
        response.raise_for_status()
        result = response.json()
    except (httpx.HTTPError, ValueError) as error:
        logging.error("Cloudinary %s upload failed", media_label)
        raise HTTPException(502, f"{media_label.title()} upload failed. Please try again.") from error

    secure_url = result.get("secure_url") if isinstance(result, dict) else None
    if not isinstance(secure_url, str) or not secure_url.startswith("https://"):
        logging.error("Cloudinary returned an invalid %s URL", media_label)
        raise HTTPException(502, f"{media_label.title()} upload failed. Please try again.")
    return secure_url


def upload_image(image: bytes, content_type: str, public_id: str) -> str:
    return _upload_media(image, content_type, public_id, "image", "image")


def upload_video(video: bytes, content_type: str, public_id: str) -> str:
    return _upload_media(video, content_type, public_id, "video", "video")
