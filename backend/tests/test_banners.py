from app.services.rate_limit import _hits


def login(client, email):
    _hits.clear()
    return client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "WorkBitDev123!"},
    )


def test_dashboard_banners_are_admin_managed_and_only_published_are_visible(client):
    assert login(client, "workbit-admin@example.com").status_code == 200
    admin_list = client.get("/api/v1/admin/dashboard-banners")
    assert admin_list.status_code == 200
    assert admin_list.json() == []

    draft = client.post(
        "/api/v1/admin/dashboard-banners",
        json={
            "title": "Draft",
            "content": "Not live",
            "image_url": "https://res.cloudinary.com/workbit/banner.png",
        },
    )
    assert draft.status_code == 201
    banner_id = draft.json()["id"]

    active = client.post(
        "/api/v1/admin/dashboard-banners",
        json={
            "title": "Welcome",
            "content": "A new announcement",
            "image_url": "https://res.cloudinary.com/workbit/banner-2.png",
            "link_url": "/offers",
            "is_active": True,
            "sort_order": 2,
        },
    )
    assert active.status_code == 201

    assert client.get("/api/v1/dashboard/banners").json() == [active.json()]
    updated = client.post(
        f"/api/v1/admin/dashboard-banners/{active.json()['id']}",
        json={
            "title": "Welcome updated",
            "content": "Updated announcement",
            "image_url": "https://res.cloudinary.com/workbit/banner-2.png",
            "link_url": "/offers",
            "is_active": False,
            "sort_order": 2,
        },
    )
    assert updated.status_code == 200
    assert client.get("/api/v1/dashboard/banners").json() == []

    deleted = client.post(f"/api/v1/admin/dashboard-banners/{banner_id}/delete")
    assert deleted.status_code == 204
    assert client.get("/api/v1/admin/dashboard-banners").json() == [updated.json()]


def test_dashboard_banner_admin_routes_require_admin_and_validate_image(client, monkeypatch):
    assert client.get("/api/v1/admin/dashboard-banners").status_code == 401
    assert login(client, "workbit-user@example.com").status_code == 200
    assert client.get("/api/v1/admin/dashboard-banners").status_code == 403
    assert client.post(
        "/api/v1/admin/dashboard-banners/upload-image",
        files={"file": ("banner.png", b"\x89PNG\r\n\x1a\nimage", "image/png")},
    ).status_code == 403

    assert login(client, "workbit-admin@example.com").status_code == 200
    monkeypatch.setattr(
        "app.api.banners.upload_image",
        lambda *_args: "https://res.cloudinary.com/workbit/banner.png",
    )
    uploaded = client.post(
        "/api/v1/admin/dashboard-banners/upload-image",
        files={"file": ("banner.png", b"\x89PNG\r\n\x1a\nimage", "image/png")},
    )
    assert uploaded.status_code == 200
    assert uploaded.json()["image_url"] == "https://res.cloudinary.com/workbit/banner.png"

    invalid = client.post(
        "/api/v1/admin/dashboard-banners",
        json={
            "title": "Unsafe link",
            "image_url": "http://example.com/banner.png",
            "link_url": "javascript:alert(1)",
        },
    )
    assert invalid.status_code == 422

