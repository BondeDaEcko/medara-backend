"""Password hashing and JWT token utilities."""

from __future__ import annotations

import logging
import warnings
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

# Suppress passlib's cosmetic warning about bcrypt.__about__ removal in bcrypt 4.x
logging.getLogger("passlib.handlers.bcrypt").setLevel(logging.ERROR)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Return bcrypt hash of plain_password."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if plain_password matches hashed_password."""
    return pwd_context.verify(plain_password, hashed_password)


def _create_token(data: dict[str, Any], expires_delta: timedelta) -> str:
    payload = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    payload.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_access_token(subject: str, role: str) -> str:
    """Create a short-lived JWT access token."""
    return _create_token(
        {"sub": subject, "role": role, "type": "access"},
        timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(subject: str) -> str:
    """Create a long-lived JWT refresh token."""
    return _create_token(
        {"sub": subject, "type": "refresh"},
        timedelta(days=settings.refresh_token_expire_days),
    )


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token. Raises JWTError on failure."""
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])


def get_token_expiry_datetime(days: int = 0, minutes: int = 0) -> datetime:
    """Return UTC datetime offset by given days/minutes."""
    return datetime.now(timezone.utc) + timedelta(days=days, minutes=minutes)
