import pytest


@pytest.mark.asyncio
async def test_register(client):
    res = await client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "testpass123",
    })
    assert res.status_code == 201
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate(client):
    await client.post("/api/auth/register", json={
        "email": "dup@example.com",
        "password": "testpass123",
    })
    res = await client.post("/api/auth/register", json={
        "email": "dup@example.com",
        "password": "testpass123",
    })
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_login(client):
    await client.post("/api/auth/register", json={
        "email": "login@example.com",
        "password": "testpass123",
    })
    res = await client.post("/api/auth/login", json={
        "email": "login@example.com",
        "password": "testpass123",
    })
    assert res.status_code == 200
    assert "access_token" in res.json()


@pytest.mark.asyncio
async def test_login_invalid(client):
    res = await client.post("/api/auth/login", json={
        "email": "noone@example.com",
        "password": "wrong",
    })
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client):
    reg = await client.post("/api/auth/register", json={
        "email": "me@example.com",
        "password": "testpass123",
    })
    token = reg.json()["access_token"]

    res = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["email"] == "me@example.com"


@pytest.mark.asyncio
async def test_create_api_key(client):
    reg = await client.post("/api/auth/register", json={
        "email": "apikey@example.com",
        "password": "testpass123",
    })
    token = reg.json()["access_token"]

    res = await client.post(
        "/api/auth/api-keys",
        json={"name": "test key"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["raw_key"].startswith("vf_live_")
    assert data["name"] == "test key"
