"""Unit tests for Pydantic request/response schemas."""

import pytest
from pydantic import ValidationError

from app.schemas.auth import UserLogin, UserRegister


def test_user_register_valid():
    data = UserRegister(email="user@example.com", password="password123", full_name="Alice")
    assert data.email == "user@example.com"
    assert data.full_name == "Alice"
    assert data.phone is None


def test_user_register_password_too_short():
    with pytest.raises(ValidationError):
        UserRegister(email="user@example.com", password="short", full_name="Alice")


def test_user_register_password_too_long():
    with pytest.raises(ValidationError):
        UserRegister(email="user@example.com", password="x" * 129, full_name="Alice")


def test_user_register_invalid_email():
    with pytest.raises(ValidationError):
        UserRegister(email="not-an-email", password="password123", full_name="Alice")


def test_user_register_empty_full_name():
    with pytest.raises(ValidationError):
        UserRegister(email="user@example.com", password="password123", full_name="")


def test_user_login_valid():
    data = UserLogin(email="user@example.com", password="anything")
    assert data.email == "user@example.com"
    assert data.password == "anything"


def test_user_login_invalid_email():
    with pytest.raises(ValidationError):
        UserLogin(email="bad-email", password="anything")
