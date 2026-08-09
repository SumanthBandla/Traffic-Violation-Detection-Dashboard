"""Violation management endpoints."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.models import Evidence, Violation
from app.db.session import get_db
from app.schemas.schemas import ViolationCreate, ViolationOut

router = APIRouter(prefix="/violations", tags=["violations"])


def _to_out(violation: Violation, db: Session) -> ViolationOut:
    evidence = (
        db.query(Evidence)
        .filter(Evidence.violation_id_fk == violation.id)
        .order_by(Evidence.id)
        .all()
    )
    out = ViolationOut.model_validate(violation)
    out.evidence = evidence
    return out


@router.get("", response_model=list[ViolationOut])
def list_violations(
    camera_id: Optional[int] = Query(None),
    violation_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Violation)
    if camera_id:
        query = query.filter(Violation.camera_id == camera_id)
    if violation_type:
        query = query.filter(Violation.violation_type == violation_type)
    if status:
        query = query.filter(Violation.status == status)
    rows = query.order_by(Violation.detected_at.desc()).offset(offset).limit(limit).all()
    return [_to_out(v, db) for v in rows]


@router.get("/{violation_id}", response_model=ViolationOut)
def get_violation(violation_id: str, db: Session = Depends(get_db)):
    violation = db.query(Violation).filter(Violation.violation_id == violation_id).first()
    if violation is None:
        violation = db.get(Violation, int(violation_id) if violation_id.isdigit() else -1)
    if violation is None:
        raise HTTPException(status_code=404, detail="Violation not found")
    return _to_out(violation, db)


@router.post("", response_model=ViolationOut, status_code=201)
def create_violation(
    payload: ViolationCreate,
    db: Session = Depends(get_db),
):
    from app.services.violation_store import next_violation_id

    violation = Violation(
        violation_id=payload.violation_id or next_violation_id(),
        violation_type=payload.violation_type,
        description=payload.description,
        confidence=payload.confidence,
        status=payload.status,
        camera_id=payload.camera_id,
        vehicle_id=payload.vehicle_id,
        lane_number=payload.lane_number,
        location=payload.location,
        detected_at=payload.detected_at,
    )
    db.add(violation)
    db.commit()
    db.refresh(violation)
    return _to_out(violation, db)
