"""Comprehensive conversion tests covering upload, download, share, batch, color analysis."""
import io
import pytest
from PIL import Image


def _make_test_image(width=100, height=100, color=(255, 0, 0)) -> bytes:
    """Create a minimal test PNG image."""
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_two_color_image() -> bytes:
    """Create an image with 2 distinct colors (red on white) for layer testing."""
    img = Image.new("RGB", (200, 200), (255, 255, 255))
    # Draw a red rectangle in the center
    for x in range(50, 150):
        for y in range(50, 150):
            img.putpixel((x, y), (200, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def _register(client) -> str:
    """Register and return JWT token."""
    import uuid
    email = f"test-{uuid.uuid4().hex[:8]}@test.io"
    res = await client.post("/api/auth/register", json={"email": email, "password": "pass1234"})
    return res.json()["access_token"]


# ── Upload Tests ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_upload_png(client):
    img = _make_test_image()
    res = await client.post(
        "/api/conversions",
        files={"file": ("test.png", img, "image/png")},
        data={"colormode": "color", "detail_level": "5", "smoothing": "5"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "pending"
    assert data["original_filename"] == "test.png"
    assert data["original_format"] == "png"
    assert data["original_size_bytes"] > 0


@pytest.mark.asyncio
async def test_upload_jpg(client):
    img = Image.new("RGB", (50, 50), (0, 0, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    res = await client.post(
        "/api/conversions",
        files={"file": ("test.jpg", buf.getvalue(), "image/jpeg")},
    )
    assert res.status_code == 201
    assert res.json()["original_format"] == "jpg"


@pytest.mark.asyncio
async def test_upload_bmp(client):
    img = Image.new("RGB", (50, 50), (0, 255, 0))
    buf = io.BytesIO()
    img.save(buf, format="BMP")
    res = await client.post(
        "/api/conversions",
        files={"file": ("test.bmp", buf.getvalue(), "image/bmp")},
    )
    assert res.status_code == 201


@pytest.mark.asyncio
async def test_upload_rejects_pdf(client):
    res = await client.post(
        "/api/conversions",
        files={"file": ("test.pdf", b"fake pdf content", "application/pdf")},
    )
    assert res.status_code == 415


@pytest.mark.asyncio
async def test_upload_anonymous_allowed(client):
    """Upload without auth should work (anonymous conversion)."""
    img = _make_test_image()
    res = await client.post(
        "/api/conversions",
        files={"file": ("anon.png", img, "image/png")},
    )
    assert res.status_code == 201
    assert res.json()["status"] == "pending"


@pytest.mark.asyncio
async def test_upload_with_settings(client):
    img = _make_test_image()
    res = await client.post(
        "/api/conversions",
        files={"file": ("test.png", img, "image/png")},
        data={"colormode": "binary", "detail_level": "9", "smoothing": "3"},
    )
    assert res.status_code == 201
    settings = res.json()["settings"]
    assert settings["colormode"] == "binary"
    assert settings["detail_level"] == 9
    assert settings["smoothing"] == 3


# ── Color Analysis ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_analyze_colors(client):
    img = _make_two_color_image()
    res = await client.post(
        "/api/conversions/analyze-colors",
        files={"file": ("test.png", img, "image/png")},
    )
    assert res.status_code == 200
    data = res.json()
    assert "colors" in data
    assert len(data["colors"]) >= 2
    assert data["total_pixels"] == 200 * 200
    assert "recommendation" in data


@pytest.mark.asyncio
async def test_analyze_colors_rejects_invalid(client):
    res = await client.post(
        "/api/conversions/analyze-colors",
        files={"file": ("test.txt", b"not an image", "text/plain")},
    )
    assert res.status_code == 415


# ── Get / List ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_conversion(client):
    img = _make_test_image()
    upload = await client.post(
        "/api/conversions",
        files={"file": ("test.png", img, "image/png")},
    )
    conv_id = upload.json()["id"]
    res = await client.get(f"/api/conversions/{conv_id}")
    assert res.status_code == 200
    assert res.json()["id"] == conv_id


@pytest.mark.asyncio
async def test_get_nonexistent_conversion(client):
    res = await client.get("/api/conversions/nonexistent-id-12345")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_list_requires_auth(client):
    res = await client.get("/api/conversions")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_list_with_auth(client):
    token = await _register(client)
    img = _make_test_image()
    await client.post(
        "/api/conversions",
        files={"file": ("test.png", img, "image/png")},
        headers={"Authorization": f"Bearer {token}"},
    )
    res = await client.get(
        "/api/conversions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "conversions" in data
    assert data["total"] >= 1
    assert data["page"] == 1


# ── Batch ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_batch_requires_auth(client):
    img = _make_test_image()
    res = await client.post(
        "/api/conversions/batch",
        files=[("files", ("a.png", img, "image/png")), ("files", ("b.png", img, "image/png"))],
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_batch_upload(client):
    token = await _register(client)
    img = _make_test_image()
    res = await client.post(
        "/api/conversions/batch",
        files=[("files", ("a.png", img, "image/png")), ("files", ("b.png", img, "image/png"))],
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["total"] == 2
    assert len(data["conversions"]) == 2
    assert data["batch_id"] is not None


# ── Share ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_share_requires_auth(client):
    res = await client.post("/api/conversions/fake-id/share")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_share_nonexistent(client):
    token = await _register(client)
    res = await client.post(
        "/api/conversions/nonexistent-id/share",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_shared_link_invalid_token(client):
    res = await client.get("/api/s/invalid-token-xyz")
    assert res.status_code == 404


# ── Webhooks ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_webhook_crud(client):
    token = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    # Create
    res = await client.post("/api/webhooks", json={"url": "https://example.com/hook"}, headers=headers)
    assert res.status_code == 201
    wh_id = res.json()["id"]
    assert res.json()["url"] == "https://example.com/hook"

    # List
    res = await client.get("/api/webhooks", headers=headers)
    assert res.status_code == 200
    assert len(res.json()) >= 1

    # Update
    res = await client.put(f"/api/webhooks/{wh_id}", json={"url": "https://example.com/new"}, headers=headers)
    assert res.status_code == 200
    assert res.json()["url"] == "https://example.com/new"

    # Delete
    res = await client.delete(f"/api/webhooks/{wh_id}", headers=headers)
    assert res.status_code == 204


# ── Usage / Billing ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_usage_requires_auth(client):
    res = await client.get("/api/usage")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_usage(client):
    token = await _register(client)
    res = await client.get("/api/usage", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert "total_conversions" in data
    assert "successful_conversions" in data


@pytest.mark.asyncio
async def test_usage_history(client):
    token = await _register(client)
    res = await client.get("/api/usage/history?months=3", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert "history" in res.json()
