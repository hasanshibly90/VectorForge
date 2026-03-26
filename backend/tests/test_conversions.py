import pytest


@pytest.mark.asyncio
async def test_health(client):
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_upload_no_file(client):
    res = await client.post("/api/conversions")
    assert res.status_code == 422  # Missing file


@pytest.mark.asyncio
async def test_upload_invalid_format(client):
    res = await client.post(
        "/api/conversions",
        files={"file": ("test.txt", b"not an image", "text/plain")},
    )
    assert res.status_code == 415


@pytest.mark.asyncio
async def test_list_conversions_requires_auth(client):
    res = await client.get("/api/conversions")
    assert res.status_code == 401
