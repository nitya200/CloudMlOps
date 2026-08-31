"""Password hashing and JWT issuing/verification."""

from __future__ import annotations

import base64
import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.core.config import settings
from app.core.exceptions import AuthenticationError


def _prehash(password: str) -> bytes:
    """Compress the password to a fixed 44 byte token before bcrypt.

    bcrypt silently truncates anything past 72 bytes; SHA-256 + base64 keeps the
    full entropy of long passwords and avoids that footgun.
    """
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    return base64.b64encode(digest)


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=settings.bcrypt_rounds)
    return bcrypt.hashpw(_prehash(password), salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_prehash(password), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(
    subject: str | uuid.UUID,
    *,
    role: str,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> tuple[str, datetime, str]:
    """Return ``(token, expires_at, jti)``.

    The ``jti`` is persisted as a Session row so logout can revoke the token
    server side rather than relying on the client discarding it.
    """
    now = datetime.now(UTC)
    expires_at = now + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    jti = secrets.token_urlsafe(24)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": jti,
        **(extra_claims or {}),
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, expires_at, jti


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("Session has expired, please sign in again.") from exc
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Invalid authentication credentials.") from exc
