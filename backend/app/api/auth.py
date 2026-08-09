"""Authentication endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.security import create_access_token, verify_password
from app.db.models import User
from app.db.session import get_db
from app.schemas.schemas import LoginRequest, LoginResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        record_audit(
            db, actor=payload.username or "unknown", action="login_failed",
            resource="auth", resource_id=payload.username or "",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")
    token = create_access_token(user.username, user.role)
    record_audit(db, actor=user.username, action="login", resource="auth", resource_id=str(user.id))
    return LoginResponse(access_token=token, user=UserOut.model_validate(user))
