"""Integration tests for /bookings routes."""

import uuid
from unittest.mock import MagicMock

from httpx import AsyncClient

from app.auth.security import create_access_token
from tests.conftest import make_fake_user


async def test_my_bookings_requires_auth(client: AsyncClient):
    response = await client.get("/bookings/me")
    assert response.status_code == 401


async def test_host_bookings_requires_auth(client: AsyncClient):
    response = await client.get("/bookings/host")
    assert response.status_code == 401


async def test_create_booking_requires_auth(client: AsyncClient):
    response = await client.post(
        "/bookings",
        json={
            "property_id": str(uuid.uuid4()),
            "check_in": "2025-12-01",
            "check_out": "2025-12-05",
            "num_guests": 2,
        },
    )
    assert response.status_code == 401


async def test_cancel_booking_requires_auth(client: AsyncClient):
    response = await client.patch(f"/bookings/{uuid.uuid4()}/cancel")
    assert response.status_code == 401


async def test_my_bookings_returns_empty_list(client: AsyncClient, mock_db):
    user_id = uuid.uuid4()
    fake_user = make_fake_user(id=user_id)
    token = create_access_token(str(user_id))

    # get_current_user query returns our fake user
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = fake_user

    # bookings query returns empty list
    bookings_result = MagicMock()
    bookings_result.scalars.return_value.all.return_value = []

    mock_db.execute.side_effect = [user_result, bookings_result]

    response = await client.get("/bookings/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == []
