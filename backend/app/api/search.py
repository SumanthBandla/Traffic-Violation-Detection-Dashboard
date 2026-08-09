"""Search endpoints for plates, cameras and violations."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.models import Camera, Vehicle, Violation
from app.db.session import get_db
from app.schemas.schemas import ViolationOut

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/plates/{plate}")
def search_plates(plate: str, db: Session = Depends(get_db)):
    vehicles = (
        db.query(Vehicle)
        .filter(Vehicle.plate_number.ilike(f"%{plate}%"))
        .limit(50)
        .all()
    )
    return [
        {
            "id": v.id,
            "plate_number": v.plate_number,
            "vehicle_type": v.vehicle_type,
            "brand": v.brand,
            "model": v.model,
            "color": v.color,
            "owner_name": v.owner_name,
        }
        for v in vehicles
    ]


@router.get("/violations")
def search_violations(
    q: Optional[str] = None,
    camera_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Violation)
    if camera_id:
        query = query.filter(Violation.camera_id == camera_id)
    if q:
        query = query.filter(
            or_(
                Violation.violation_id.ilike(f"%{q}%"),
                Violation.violation_type.ilike(f"%{q}%"),
                Violation.location.ilike(f"%{q}%"),
                Violation.description.ilike(f"%{q}%"),
            )
        )
    rows = query.order_by(Violation.detected_at.desc()).limit(100).all()
    return [ViolationOut.model_validate(v) for v in rows]
