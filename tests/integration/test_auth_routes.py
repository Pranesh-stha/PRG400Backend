"""Integration tests for /auth routes using a mocked database session."""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient

from app.auth.security import create_access_token, hash_password
from tests.conftest import make_fake_user


async def test_register_success(client: AsyncClient, mock_db):
    # DB reports no existing user → registration succeeds
    mock_db.execute.return_value.scalar_one_or_none.return_value = None

    response = await client.post(
        "/auth/register",
        json={"email": "new@example.com", "password": "password123", "full_name": "New User"},
    )
    assert response.status_code == 201
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "new@example.com"


async def test_register_duplicate_email_returns_409(client: AsyncClient, mock_db):
    existing = make_fake_user(email="taken@example.com")
    mock_db.execute.return_value.scalar_one_or_none.return_value = existing

    response = await client.post(
        "/auth/register",
        json={"email": "taken@example.com", "password": "password123", "full_name": "User"},
    )
    assert response.status_code == 409


async def test_register_invalid_payload_returns_422(client: AsyncClient):
    response = await client.post(
        "/auth/register",
        json={"email": "not-an-email", "password": "short", "full_name": ""},
    )
    assert response.status_code == 422


async def test_login_success(client: AsyncClient, mock_db):
    fake_user = make_fake_user(
        email="login@example.com",
        password_hash=hash_password("correctpassword"),
    )
    mock_db.execute.return_value.scalar_one_or_none.return_value = fake_user

    response = await client.post(
        "/auth/login",
        json={"email": "login@example.com", "password": "correctpassword"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


async def test_login_wrong_password_returns_401(client: AsyncClient, mock_db):
    fake_user = make_fake_user(
        email="login@example.com",
        password_hash=hash_password("correctpassword"),
    )
    mock_db.execute.return_value.scalar_one_or_none.return_value = fake_user

    response = await client.post(
        "/auth/login",
        json={"email": "login@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401


async def test_login_nonexistent_user_returns_401(client: AsyncClient, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = None

    response = await client.post(
        "/auth/login",
        json={"email": "nobody@example.com", "password": "anything"},
    )
    assert response.status_code == 401


async def test_me_without_token_returns_401(client: AsyncClient):
    response = await client.get("/auth/me")
    assert response.status_code == 401


async def test_me_with_valid_token_returns_user(client: AsyncClient, mock_db):
    user_id = uuid.uuid4()
    fake_user = make_fake_user(id=user_id, email="me@example.com")
    mock_db.execute.return_value.scalar_one_or_none.return_value = fake_user

    token = create_access_token(str(user_id))
    response = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"


async def test_me_with_invalid_token_returns_401(client: AsyncClient):
    response = await client.get("/auth/me", headers={"Authorization": "Bearer invalidtoken"})
    assert response.status_code == 401
