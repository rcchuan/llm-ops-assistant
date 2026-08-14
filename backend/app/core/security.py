from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash


MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128
password_hash = PasswordHash.recommended()


def validate_password_strength(password: str) -> None:
    if not MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH:
        raise ValueError(f"密码长度必须为 {MIN_PASSWORD_LENGTH}～{MAX_PASSWORD_LENGTH} 位")
    if not any(character.isalpha() for character in password):
        raise ValueError("密码必须包含字母")
    if not any(character.isdigit() for character in password):
        raise ValueError("密码必须包含数字")


def hash_password(password: str) -> str:
    validate_password_strength(password)
    return password_hash.hash(password)


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        return password_hash.verify(password, encoded_hash)
    except (ValueError, TypeError):
        return False


def create_access_token(
    *,
    user_id: int,
    username: str,
    role: str,
    token_version: int,
    secret_key: str,
    algorithm: str,
    expires_delta: timedelta = timedelta(minutes=120),
) -> str:
    expires_at = datetime.now(UTC) + expires_delta
    return jwt.encode(
        {
            "sub": str(user_id),
            "username": username,
            "role": role,
            "token_version": token_version,
            "exp": expires_at,
        },
        secret_key,
        algorithm=algorithm,
    )


def decode_access_token(token: str, secret_key: str, algorithm: str) -> dict:
    return jwt.decode(
        token,
        secret_key,
        algorithms=[algorithm],
        options={"require": ["sub", "username", "role", "token_version", "exp"]},
    )
