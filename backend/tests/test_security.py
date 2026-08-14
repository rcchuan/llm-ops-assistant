from datetime import timedelta

import jwt
import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    validate_password_strength,
    verify_password,
)


TEST_SECRET = "test-secret-key-long-enough-for-hs256"


@pytest.mark.parametrize(
    "password",
    ["short1", "onlyletters", "12345678", "a1" * 65],
)
def test_password_rule_rejects_invalid_password(password: str) -> None:
    with pytest.raises(ValueError):
        validate_password_strength(password)


def test_password_hash_is_not_plaintext_and_can_be_verified() -> None:
    password = "ValidPass123"

    password_hash = hash_password(password)

    assert password_hash != password
    assert verify_password(password, password_hash) is True
    assert verify_password("WrongPass123", password_hash) is False


def test_jwt_contains_required_claims() -> None:
    token = create_access_token(
        user_id=7,
        username="operator01",
        role="operator",
        token_version=0,
        secret_key=TEST_SECRET,
        algorithm="HS256",
        expires_delta=timedelta(minutes=120),
    )

    claims = decode_access_token(token, TEST_SECRET, "HS256")

    assert claims["sub"] == "7"
    assert claims["username"] == "operator01"
    assert claims["role"] == "operator"
    assert claims["token_version"] == 0
    assert "exp" in claims


def test_jwt_rejects_expired_and_invalid_signature() -> None:
    expired = create_access_token(
        user_id=7,
        username="operator01",
        role="operator",
        token_version=0,
        secret_key=TEST_SECRET,
        algorithm="HS256",
        expires_delta=timedelta(seconds=-1),
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(expired, TEST_SECRET, "HS256")
    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(
            create_access_token(
                user_id=7,
                username="operator01",
                role="operator",
                token_version=0,
                secret_key=TEST_SECRET,
                algorithm="HS256",
            ),
            "different-test-secret-that-is-long-enough",
            "HS256",
        )


def test_jwt_rejects_missing_token_version() -> None:
    token = jwt.encode(
        {
            "sub": "7",
            "username": "operator01",
            "role": "operator",
            "exp": 4102444800,
        },
        TEST_SECRET,
        algorithm="HS256",
    )

    with pytest.raises(jwt.MissingRequiredClaimError):
        decode_access_token(token, TEST_SECRET, "HS256")
