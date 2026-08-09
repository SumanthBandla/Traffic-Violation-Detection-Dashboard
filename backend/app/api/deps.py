"""FastAPI dependencies: current user and RBAC guards."""
from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.models import User
from app.db.session import get_db, get_session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_token(token)
        username = payload.get("sub")
        if not username:
            raise JWTError("missing subject")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(User).filter(User.username == username).first()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")
    return user


def require_roles(*roles: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return user

    return checker


def resolve_token(token: Optional[str]) -> Optional[User]:
    """Resolve a JWT to a User without raising (used by WebSocket auth)."""
    if not token:
        return None
    try:
        payload = decode_token(token)
        username = payload.get("sub")
        if not username:
            return None
        db = get_session()
        try:
            return db.query(User).filter(User.username == username).first()
        finally:
            db.close()
    except Exception:
        return None


def authenticate_websocket(token: str) -> User:
    """Raise if the token is invalid; used by guarded WebSocket endpoints."""
    user = resolve_token(token)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return user
