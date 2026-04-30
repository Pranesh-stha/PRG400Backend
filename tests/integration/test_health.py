"""Integration tests for meta endpoints (no auth, no DB)."""

from httpx import AsyncClient


async def test_root_returns_ok(client: AsyncClient):
    response = await client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "Travel Booking" in body["name"]


async def test_health_returns_ok(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "connected"
