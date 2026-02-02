"""
Security helper tests (JWT + password hashing).
"""

import time

from src.middleware.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)


def test_password_hash_roundtrip():
    hashed = hash_password("pw123")
    assert hashed != "pw123"
    assert verify_password("pw123", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_jwt_create_and_decode_contains_subject():
    token = create_access_token({"sub": "user-123"})
    payload = decode_access_token(token)
    assert payload["sub"] == "user-123"
    assert "exp" in payload


def test_jwt_decode_invalid_returns_none():
    assert decode_access_token("not-a-jwt") is None

