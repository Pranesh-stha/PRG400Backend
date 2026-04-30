"""Unit tests for app.auth.security — pure functions, no DB or HTTP needed."""

import pytest

from app.auth.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_password_is_not_plaintext():
    hashed = hash_password("supersecret")
    assert hashed != "supersecret"
    assert isinstance(hashed, str)
    assert len(hashed) > 0


def test_hash_password_produces_unique_hashes():
    h1 = hash_password("same-password")
    h2 = hash_password("same-password")
    # bcrypt uses a random salt each time
    assert h1 != h2


def test_verify_password_correct():
    hashed = hash_password("correct-horse-battery")
    assert verify_password("correct-horse-battery", hashed) is True


def test_verify_password_wrong():
    hashed = hash_password("correct-horse-battery")
    assert verify_password("wrong-password", hashed) is False


def test_create_and_decode_access_token_round_trip():
    subject = "user-id-abc-123"
    token = create_access_token(subject)
    payload = decode_access_token(token)
    assert payload["sub"] == subject


def test_decode_invalid_token_raises_value_error():
    with pytest.raises(ValueError, match="Invalid or expired token"):
        decode_access_token("not.a.valid.jwt.token")


def test_decode_tampered_token_raises_value_error():
    token = create_access_token("user-999")
    # Corrupt the signature
    tampered = token[:-4] + "XXXX"
    with pytest.raises(ValueError):
        decode_access_token(tampered)
