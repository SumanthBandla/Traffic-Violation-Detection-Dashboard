"""Dashboard analytics endpoints."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import Camera, DetectionLog, Evidence, User, Violation
from app.db.session import get_db

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
def dashboard_stats(days: int = Query(7, ge=1, le=365), db: Session = Depends(get_db)):
    since = datetime.utcnow() - timedelta(days=days)

    total_violations = db.query(func.count(Violation.id)).scalar() or 0
    recent_violations = (
        db.query(func.count(Violation.id))
        .filter(Violation.created_at >= since)
        .scalar()
        or 0
    )
    active_cameras = db.query(func.count(Camera.id)).filter(Camera.status == "online").scalar() or 0
    total_cameras = db.query(func.count(Camera.id)).scalar() or 0
    total_users = db.query(func.count(User.id)).scalar() or 0

    by_type = (
        db.query(Violation.violation_type, func.count(Violation.id))
        .filter(Violation.created_at >= since)
        .group_by(Violation.violation_type)
        .all()
    )
    by_status = (
        db.query(Violation.status, func.count(Violation.id))
        .filter(Violation.created_at >= since)
        .group_by(Violation.status)
        .all()
    )

    violations_by_day = (
        db.query(func.date(Violation.created_at), func.count(Violation.id))
        .filter(Violation.created_at >= since)
        .group_by(func.date(Violation.created_at))
        .all()
    )

    return {
        "total_violations": total_violations,
        "recent_violations": recent_violations,
        "active_cameras": active_cameras,
        "total_cameras": total_cameras,
        "mobile_cameras": db.query(func.count(Camera.id)).filter(Camera.camera_type == "mobile").scalar() or 0,
        "fixed_cameras": db.query(func.count(Camera.id)).filter(Camera.camera_type == "fixed").scalar() or 0,
        "total_users": total_users,
        "violations_by_type": [{"type": t, "count": c} for t, c in by_type],
        "violations_by_status": [{"status": s, "count": c} for s, c in by_status],
        "violations_by_day": [{"date": str(d), "count": c} for d, c in violations_by_day],
    }


@router.get("/heatmap")
def dashboard_heatmap(db: Session = Depends(get_db)):
    rows = (
        db.query(Camera, func.count(Violation.id))
        .outerjoin(Violation, Violation.camera_id == Camera.id)
        .group_by(Camera.id)
        .all()
    )
    points = [
        {
            "lat": camera.latitude or 0.0,
            "lng": camera.longitude or 0.0,
            "value": count,
            "label": camera.name,
            "camera_id": camera.id,
            "camera_type": camera.camera_type,
        }
        for camera, count in rows
    ]
    return {"points": points}
