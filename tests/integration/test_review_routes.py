"""Integration tests for /reviews routes."""

import uuid
from unittest.mock import MagicMock

from httpx import AsyncClient


async def test_list_property_reviews_empty(client: AsyncClient, mock_db):
    # Returns a list of (Review, User) tuples — empty here
    result = MagicMock()
    result.all.return_value = []
    mock_db.execute.return_value = result

    property_id = uuid.uuid4()
    response = await client.get(f"/reviews/property/{property_id}")
    assert response.status_code == 200
    assert response.json() == []


async def test_create_review_requires_auth(client: AsyncClient):
    response = await client.post(
        "/reviews",
        json={"booking_id": str(uuid.uuid4()), "rating": 5, "comment": "Great!"},
    )
    assert response.status_code == 401


async def test_list_reviews_with_pagination(client: AsyncClient, mock_db):
    result = MagicMock()
    result.all.return_value = []
    mock_db.execute.return_value = result

    property_id = uuid.uuid4()
    response = await client.get(f"/reviews/property/{property_id}?limit=5&offset=0")
    assert response.status_code == 200


async def test_list_reviews_invalid_limit(client: AsyncClient, mock_db):
    property_id = uuid.uuid4()
    # limit=0 is below the ge=1 constraint
    response = await client.get(f"/reviews/property/{property_id}?limit=0")
    assert response.status_code == 422
