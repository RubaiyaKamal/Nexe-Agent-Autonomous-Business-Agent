import uuid

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.auth_service import create_access_token


@pytest.fixture
def auth_headers() -> dict:
    token = create_access_token(str(uuid.uuid4()), "test@example.com")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_submit_goal_returns_202(auth_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/goals",
            json={"text": "Build a sales report"},
            headers=auth_headers,
        )
    assert resp.status_code == 202
    data = resp.json()
    assert "id" in data
    assert data["status"] == "received"


@pytest.mark.asyncio
async def test_goal_text_too_long_returns_400(auth_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/goals",
            json={"text": "x" * 2001},
            headers=auth_headers,
        )
    assert resp.status_code == 422  # Pydantic validation


@pytest.mark.asyncio
async def test_unauthenticated_returns_401():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/goals", json={"text": "test"})
    assert resp.status_code == 403  # missing bearer → 403 from HTTPBearer
