"""Evidence retrieval and streaming."""
from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import resolve_token
from app.db.models import Evidence
from app.db.session import get_db
from fastapi.security import OAuth2PasswordBearer

router = APIRouter(prefix="/evidence", tags=["evidence"])

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

VIEWER_ROLES = {"admin", "officer", "analyst"}


def _authenticated(token: Optional[str]) -> bool:
    if not token:
        return False
    user = resolve_token(token)
    return user is not None and user.role in VIEWER_ROLES


@router.get("/{evidence_id}/content")
def evidence_content(
    evidence_id: int,
    token: str = Query(""),
    bearer: Optional[str] = Depends(oauth2),
    db: Session = Depends(get_db),
):
    """Serve an evidence image.

    Authentication is accepted via the ``Authorization: Bearer`` header or the
    ``?token=`` query parameter so ``<img>`` tags can load content directly.
    """
    if not _authenticated(bearer) and not _authenticated(token):
        raise HTTPException(status_code=401, detail="Not authenticated")

    evidence = db.get(Evidence, evidence_id)
    if evidence is None:
        raise HTTPException(status_code=404, detail="Evidence not found")
    if not os.path.exists(evidence.path):
        raise HTTPException(status_code=404, detail="Evidence file missing")
    if evidence.encrypted:
        raise HTTPException(status_code=403, detail="Encrypted evidence cannot be served")
    return FileResponse(evidence.path, media_type=evidence.mime_type or "image/jpeg")
