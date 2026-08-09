"""Camera management endpoints, including mobile camera registration."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.db.models import Camera, User
from app.db.session import get_db
from app.schemas.schemas import (
    CameraCreate,
    CameraHeartbeat,
    CameraOut,
    CameraStreamStatus,
    CameraUpdate,
)
from app.stream.hub import get_hub

logger = logging.getLogger("app.api.cameras")
router = APIRouter(prefix="/cameras", tags=["cameras"])


def _to_out(camera: Camera) -> CameraOut:
    return CameraOut.model_validate(camera)


@router.get("", response_model=list[CameraOut])
def list_cameras(
    camera_type: Optional[str] = Query(None, description="fixed | mobile"),
    db: Session = Depends(get_db),
):
    query = db.query(Camera)
    if camera_type:
        query = query.filter(Camera.camera_type == camera_type)
    return [_to_out(c) for c in query.order_by(Camera.id).all()]


@router.get("/{camera_id}", response_model=CameraOut)
def get_camera(camera_id: int, db: Session = Depends(get_db)):
    camera = db.get(Camera, camera_id)
    if camera is None:
        raise HTTPException(status_code=404, detail="Camera not found")
    return _to_out(camera)


@router.post("", response_model=CameraOut, status_code=status.HTTP_201_CREATED)
def register_camera(
    payload: CameraCreate,
    db: Session = Depends(get_db),
):
    """Register a new camera.

    Mobile clients register themselves here with ``camera_type="mobile"`` and a
    stable ``device_id`` so a device can be re-registered without duplicates.
    """
    if payload.camera_type not in {"fixed", "mobile"}:
        raise HTTPException(status_code=422, detail="camera_type must be 'fixed' or 'mobile'")

    duplicate = None
    if payload.device_id:
        duplicate = (
            db.query(Camera)
            .filter(Camera.device_id == payload.device_id)
            .order_by(Camera.id)
            .first()
        )
    if duplicate is not None:
        if payload.name:
            duplicate.name = payload.name
        if payload.location:
            duplicate.location = payload.location
        if payload.latitude or payload.longitude:
            duplicate.latitude = payload.latitude or duplicate.latitude
            duplicate.longitude = payload.longitude or duplicate.longitude
        duplicate.camera_type = payload.camera_type
        duplicate.status = "active"
        db.commit()
        db.refresh(duplicate)
        logger.info("camera %s re-registered for device %s", duplicate.id, payload.device_id)
        return _to_out(duplicate)

    camera = Camera(
        name=payload.name,
        location=payload.location or payload.name,
        lane_number=payload.lane_number,
        latitude=payload.latitude,
        longitude=payload.longitude,
        stream_url=payload.stream_url,
        status="active",
        camera_type=payload.camera_type,
        device_id=payload.device_id,
        is_streaming=False,
    )
    db.add(camera)
    db.commit()
    db.refresh(camera)
    record_audit(
        db,
        actor="system",
        action="camera_registered",
        resource="camera",
        resource_id=str(camera.id),
        details={"camera_type": payload.camera_type, "device_id": payload.device_id},
    )
    logger.info("registered camera id=%s name=%s type=%s", camera.id, camera.name, payload.camera_type)
    return _to_out(camera)


@router.patch("/{camera_id}", response_model=CameraOut)
def update_camera(
    camera_id: int,
    payload: CameraUpdate,
    db: Session = Depends(get_db),
):
    camera = db.get(Camera, camera_id)
    if camera is None:
        raise HTTPException(status_code=404, detail="Camera not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(camera, field, value)
    db.commit()
    db.refresh(camera)
    return _to_out(camera)


@router.post("/{camera_id}/heartbeat", response_model=CameraOut)
def camera_heartbeat(
    camera_id: int,
    payload: CameraHeartbeat,
    db: Session = Depends(get_db),
):
    """Mobile camera health/GPS update. Marks the camera online."""
    camera = db.get(Camera, camera_id)
    if camera is None:
        raise HTTPException(status_code=404, detail="Camera not found")
    camera.status = "online" if payload.status == "online" else payload.status
    camera.last_seen = datetime.utcnow()
    if payload.latitude is not None:
        camera.latitude = payload.latitude
    if payload.longitude is not None:
        camera.longitude = payload.longitude
    if payload.is_streaming is not None:
        camera.is_streaming = payload.is_streaming
    db.commit()
    db.refresh(camera)
    return _to_out(camera)


@router.post("/{camera_id}/status", response_model=CameraOut)
def set_stream_status(
    camera_id: int,
    payload: CameraStreamStatus,
    db: Session = Depends(get_db),
):
    camera = db.get(Camera, camera_id)
    if camera is None:
        raise HTTPException(status_code=404, detail="Camera not found")
    camera.is_streaming = payload.is_streaming
    camera.last_seen = datetime.utcnow()
    if payload.is_streaming:
        camera.status = "online"
    db.commit()
    db.refresh(camera)
    get_hub().mark_streaming(camera_id, payload.is_streaming)
    return _to_out(camera)
