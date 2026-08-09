"""Security helpers: password hashing and JWT (RBAC) tokens."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings


def hash_password(password: str) -> str:
    """Hash a plain-text password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a stored hash.

    Supports bcrypt hashes (``$2...``) produced by this application and the
    legacy ``salt$sha256hex`` format found in the committed seed database.
    """
    try:
        if hashed_password.startswith("$2"):
            return bcrypt.checkpw(
                plain_password.encode("utf-8"), hashed_password.encode("utf-8")
            )
    except ValueError:
        return False
    if "$" in hashed_password:
        salt, digest = hashed_password.split("$", 1)
        if len(digest) == 64:
            for candidate in (salt + plain_password, plain_password + salt):
                if _sha256_hex(candidate) == digest:
                    return True
    return False


def _sha256_hex(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def create_access_token(subject: str, role: str, expires_minutes: Optional[int] = None) -> str:
    """Create a signed JWT with the user subject and role claim."""
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    settings = get_settings()
    return jwt.decode(token, settings.secret_key, algorithms=[settings.ALGORITHM])
