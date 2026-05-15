import pytest
from httpx import AsyncClient


async def _get_token(client: AsyncClient, email: str = "org@test.com") -> str:
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "pass123",
        "role": "organizer",
    })
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": "pass123"})
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_create_and_list_attempts(client: AsyncClient):
    token = await _get_token(client, "org2@test.com")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post("/api/v1/attempts", json={
        "record_title": "Longest continuous coding session",
        "category": "Technology",
    }, headers=headers)
    assert resp.status_code == 201
    attempt = resp.json()
    assert attempt["record_title"] == "Longest continuous coding session"
    assert attempt["status"] == "draft"
    assert attempt["application_ref"].startswith("GWR-")

    resp = await client.get("/api/v1/attempts", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_attempt_health(client: AsyncClient):
    token = await _get_token(client, "org3@test.com")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post("/api/v1/attempts", json={"record_title": "Health test"}, headers=headers)
    attempt_id = resp.json()["id"]

    resp = await client.get(f"/api/v1/attempts/{attempt_id}/health", headers=headers)
    assert resp.status_code == 200
    health = resp.json()
    assert "score" in health
    assert health["score"] < 100  # no witnesses, evidence, etc yet
