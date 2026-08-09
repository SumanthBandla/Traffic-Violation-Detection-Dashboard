"""Persist violation events and associated evidence from the stream pipeline."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.db.models import Camera, DetectionLog, Evidence, Violation
from app.db.session import get_session
from app.services import evidence as evidence_service

logger = logging.getLogger("app.services.violation_store")

_counter = 0


def next_violation_id() -> str:
    global _counter
    _counter += 1
    return f"V{datetime.now().strftime('%Y%m%d%H%M%S')}{_counter:05d}"


def store_violation(
    camera_id: int,
    event: dict[str, Any],
    frame_bytes: bytes,
) -> Optional[dict[str, Any]]:
    """Create a Violation row, capture evidence, and emit detection logs.

    Uses its own session so it is safe to call from worker threads.
    """
    db: Session = get_session()
    try:
        camera = db.get(Camera, camera_id)
        if camera is None:
            logger.warning("store_violation: camera %s not found", camera_id)
            return None

        violation_id = next_violation_id()
        detection = event.get("detection", {})

        violation = Violation(
            violation_id=violation_id,
            violation_type=event["violation_type"],
            description=event.get("description", ""),
            confidence=float(event.get("confidence", 0.0)),
            status="pending",
            camera_id=camera_id,
            lane_number=camera.lane_number or 1,
            location=camera.location or camera.name or "Unknown",
            detected_at=datetime.utcnow(),
        )
        db.add(violation)
        db.flush()

        meta = evidence_service.save_evidence(camera_id, violation_id, frame_bytes)
        db.add(
            Evidence(
                violation_id_fk=violation.id,
                kind=meta["kind"],
                path=meta["path"],
                mime_type=meta["mime_type"],
                encrypted=meta["encrypted"],
                captured_at=datetime.utcnow(),
            )
        )

        track_id = int(detection.get("track_id", 0) or 0)
        bbox = detection.get("bbox", [])
        db.add(
            DetectionLog(
                violation_id_fk=violation.id,
                track_id=track_id,
                object_type=detection.get("label", "vehicle"),
                confidence=float(detection.get("confidence", event.get("confidence", 0.0))),
                bbox={"coords": bbox},
                speed_kmh=float(detection.get("speed_kmh", 0.0)),
                direction="unknown",
                log_meta={"camera_id": camera_id, "camera_name": camera.name},
            )
        )
        db.commit()

        logger.info(
            "violation stored id=%s type=%s camera=%s conf=%.2f",
            violation_id, event["violation_type"], camera_id, event.get("confidence", 0.0),
        )
        return {
            "id": violation.id,
            "violation_id": violation_id,
            "violation_type": event["violation_type"],
            "description": event.get("description", ""),
            "confidence": float(event.get("confidence", 0.0)),
            "status": "pending",
            "camera_id": camera_id,
            "camera_name": camera.name,
            "location": camera.location or camera.name,
            "detected_at": datetime.utcnow().isoformat(),
        }
    except Exception:  # pragma: no cover - defensive
        db.rollback()
        logger.exception("failed to store violation")
        return None
    finally:
        db.close()
