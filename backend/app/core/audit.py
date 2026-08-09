"""Audit logging for sensitive operations."""
from __future__ import annotations

import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.db.models import AuditLog

logger = logging.getLogger("app.audit")


def record_audit(
    db: Session,
    actor: str,
    action: str,
    resource: str,
    resource_id: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> None:
    """Persist an audit entry and log it."""
    entry = AuditLog(
        actor=actor,
        action=action,
        resource=resource,
        resource_id=str(resource_id) if resource_id is not None else None,
        details=details or {},
    )
    db.add(entry)
    db.commit()
    logger.info("audit actor=%s action=%s resource=%s id=%s", actor, action, resource, resource_id)
