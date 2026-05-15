import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient):
    resp = await client.post("/api/v1/auth/register", json={
        "email": "organizer@test.com",
        "password": "testpass123",
        "role": "organizer",
        "full_name": "Test Organizer",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "organizer@test.com"
    assert data["role"] == "organizer"

    resp = await client.post("/api/v1/auth/login", json={
        "email": "organizer@test.com",
        "password": "testpass123",
    })
    assert resp.status_code == 200
    tokens = resp.json()
    assert "access_token" in tokens
    assert tokens["role"] == "organizer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "email": "user2@test.com",
        "password": "correct",
        "role": "organizer",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "user2@test.com",
        "password": "wrong",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_attempts_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/attempts")
    assert resp.status_code == 401
