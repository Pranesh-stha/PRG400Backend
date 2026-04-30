"""Integration tests for /properties routes."""

import uuid
from unittest.mock import MagicMock

from httpx import AsyncClient

from app.auth.security import create_access_token
from tests.conftest import make_fake_user


async def test_list_properties_empty(client: AsyncClient, mock_db):
    # First execute: count query → 0; second execute: list query → []
    count_result = MagicMock()
    count_result.scalar_one.return_value = 0

    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = []

    mock_db.execute.side_effect = [count_result, list_result]

    response = await client.get("/properties")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["items"] == []


async def test_list_properties_with_filters(client: AsyncClient, mock_db):
    count_result = MagicMock()
    count_result.scalar_one.return_value = 0

    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = []

    mock_db.execute.side_effect = [count_result, list_result]

    response = await client.get("/properties?city=Paris&min_price=50&max_price=200&guests=2")
    assert response.status_code == 200
    assert response.json()["total"] == 0


async def test_list_properties_invalid_date_range(client: AsyncClient, mock_db):
    count_result = MagicMock()
    count_result.scalar_one.return_value = 0
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = []
    mock_db.execute.side_effect = [count_result, list_result]

    # check_out before check_in should return 400
    response = await client.get("/properties?check_in=2025-12-10&check_out=2025-12-05")
    assert response.status_code == 400


async def test_get_property_not_found(client: AsyncClient, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = None

    property_id = uuid.uuid4()
    response = await client.get(f"/properties/{property_id}")
    assert response.status_code == 404


async def test_create_property_requires_auth(client: AsyncClient):
    response = await client.post(
        "/properties",
        json={
            "title": "Test Property",
            "description": "A nice place",
            "property_type": "apartment",
            "address": "1 Main St",
            "city": "Paris",
            "country": "France",
            "price_per_night": 100.0,
            "max_guests": 2,
            "bedrooms": 1,
            "bathrooms": 1,
            "amenities": [],
            "images": [],
        },
    )
    assert response.status_code == 401


async def test_delete_property_requires_auth(client: AsyncClient):
    response = await client.delete(f"/properties/{uuid.uuid4()}")
    assert response.status_code == 401


async def test_list_my_properties_requires_auth(client: AsyncClient):
    response = await client.get("/properties/host/me")
    assert response.status_code == 401
