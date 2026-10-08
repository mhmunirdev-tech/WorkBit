import hashlib

from app.core.config import settings
from app.services.rate_limit import _hits


def login(client):
    _hits.clear()
    return client.post(
        "/api/v1/auth/login",
        json={"email": "workbit-user@example.com", "password": "WorkBitDev123!"},
    )


def test_profile_avatar_upload_stores_secure_cloudinary_url(client, monkeypatch):
    monkeypatch.setattr(settings, "cloudinary_cloud_name", "workbit-test")
    monkeypatch.setattr(settings, "cloudinary_api_key", "test-api-key")
    monkeypatch.setattr(settings, "cloudinary_api_secret", "test-api-secret")
    calls = {}

    class CloudinaryResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"secure_url": "https://res.cloudinary.com/workbit-test/avatar.png"}

    def upload(url, *, data, files, timeout):
        calls.update(url=url, data=data, files=files, timeout=timeout)
        return CloudinaryResponse()

    monkeypatch.setattr("app.integrations.cloudinary.httpx.post", upload)
    assert login(client).status_code == 200
    user_id = client.get("/api/v1/auth/me").json()["id"]

    response = client.post(
        "/api/v1/profile/avatar",
        files={"file": ("avatar.png", b"\x89PNG\r\n\x1a\nimage-data", "image/png")},
    )

    assert response.status_code == 200
    assert response.json()["avatar_url"] == "https://res.cloudinary.com/workbit-test/avatar.png"
    assert calls["url"] == "https://api.cloudinary.com/v1_1/workbit-test/image/upload"
    assert calls["data"]["api_key"] == "test-api-key"
    assert calls["files"]["file"][2] == "image/png"
    params = {
        "invalidate": "true",
        "overwrite": "true",
        "public_id": f"workbit/avatars/{user_id}",
        "timestamp": calls["data"]["timestamp"],
    }
    signed_params = "&".join(f"{key}={value}" for key, value in sorted(params.items()))
    expected = hashlib.sha1(f"{signed_params}test-api-secret".encode()).hexdigest()
    assert calls["data"]["signature"] == expected
    assert client.get("/api/v1/dashboard").json()["user"]["avatar_url"] == response.json()["avatar_url"]


def test_profile_avatar_upload_requires_auth_and_supported_real_image(client, monkeypatch):
    monkeypatch.setattr(
        "app.integrations.cloudinary.httpx.post",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("Cloudinary must not be called")),
    )
    unauthenticated = client.post(
        "/api/v1/profile/avatar",
        files={"file": ("avatar.png", b"\x89PNG\r\n\x1a\nimage-data", "image/png")},
    )
    assert unauthenticated.status_code == 401

    assert login(client).status_code == 200
    invalid_image = client.post(
        "/api/v1/profile/avatar",
        files={"file": ("avatar.png", b"not an image", "image/png")},
    )
    assert invalid_image.status_code == 415
