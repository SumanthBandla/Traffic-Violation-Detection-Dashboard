"""Mobile camera streaming endpoints.

* ``WS /api/v1/stream/{camera_id}/ingest`` - the phone pushes JPEG frames.
  Each frame is decoded, run through the AI pipeline, and broadcast to
  dashboard viewers; violations are persisted and emitted as events.
* ``GET /api/v1/stream/{camera_id}/snapshot`` - latest annotated frame.
* ``GET /api/v1/stream/{camera_id}/status`` - stream status for the camera.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Optional

import cv2
import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.ai.pipeline import get_pipeline
from app.core.config import get_settings
from app.db.models import Camera
from app.db.session import get_db, get_session
from app.schemas.schemas import CameraStreamStatus
from app.services.violation_store import store_violation
from app.stream.hub import get_hub
from starlette.websockets import WebSocket, WebSocketDisconnect

from app.api.deps import resolve_token

logger = logging.getLogger("app.api.stream")
router = APIRouter(prefix="/stream", tags=["stream"])

_processing_locks: dict[int, asyncio.Lock] = {}


def _processing_lock(camera_id: int) -> asyncio.Lock:
    if camera_id not in _processing_locks:
        _processing_locks[camera_id] = asyncio.Lock()
    return _processing_locks[camera_id]


def _camera(db: Session, camera_id: int) -> Camera:
    camera = db.get(Camera, camera_id)
    if camera is None:
        raise HTTPException(status_code=404, detail="Camera not found")
    return camera


@router.websocket("/{camera_id}/ingest")
async def ingest_stream(websocket: WebSocket, camera_id: int):
    """Receive a live JPEG frame stream from a mobile camera."""
    token = websocket.query_params.get("token")
    user = resolve_token(token)
    if user is None:
        await websocket.close(code=4401)
        return

    db = get_session()
    camera = db.get(Camera, camera_id)
    if camera is None:
        db.close()
        await websocket.close(code=4404)
        return
    camera_name = camera.name
    db.close()

    await websocket.accept()
    hub = get_hub()
    hub.mark_streaming(camera_id, True)
    await hub.publish_event(
        {
            "type": "camera_status",
            "camera_id": camera_id,
            "camera_name": camera_name,
            "status": "streaming",
        }
    )

    db = get_session()
    cam = db.get(Camera, camera_id)
    if cam:
        cam.is_streaming = True
        cam.status = "online"
        cam.last_seen = datetime.utcnow()
        db.commit()
    db.close()

    settings = get_settings()
    pipeline = get_pipeline(camera_id)
    frames_processed = 0
    last_ack = 0.0

    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break
            if message["type"] != "websocket.receive":
                continue

            data: Any = message.get("bytes") or message.get("text")
            if data is None:
                continue

            if isinstance(data, str):
                # Control message (JSON), e.g. {"type":"control","action":"stop"}
                try:
                    control = json.loads(data)
                    if control.get("type") == "control" and control.get("action") == "stop":
                        break
                except json.JSONDecodeError:
                    pass
                continue

            async with _processing_lock(camera_id):
                result = await asyncio.get_running_loop().run_in_executor(
                    None, _decode_and_process, data, camera_id, pipeline
                )
            if result is None:
                continue

            annotated_jpeg = await asyncio.get_running_loop().run_in_executor(
                None, _encode_jpeg, result["frame"], settings.STREAM_QUALITY
            )

            frames_processed += 1
            await hub.publish_frame(
                camera_id,
                camera_name,
                annotated_jpeg,
                result["vehicle_count"],
            )

            if result["events"]:
                for event in result["events"]:
                    violation = await asyncio.get_running_loop().run_in_executor(
                        None, store_violation, camera_id, event, annotated_jpeg
                    )
                    if violation:
                        await hub.publish_event({"type": "violation", "violation": violation})

            now = asyncio.get_running_loop().time()
            if now - last_ack > 2.0:
                last_ack = now
                try:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "ack",
                                "frames": frames_processed,
                                "vehicle_count": result["vehicle_count"],
                                "processing_ms": round(result["processing_ms"], 1),
                            }
                        )
                    )
                except Exception:
                    pass
    except WebSocketDisconnect:
        pass
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("ingest error camera=%s: %s", camera_id, exc)
    finally:
        hub.mark_streaming(camera_id, False)
        await hub.publish_event(
            {
                "type": "camera_status",
                "camera_id": camera_id,
                "camera_name": camera_name,
                "status": "stopped",
            }
        )
        db = get_session()
        cam = db.get(Camera, camera_id)
        if cam:
            cam.is_streaming = False
            cam.last_seen = datetime.utcnow()
            db.commit()
        db.close()
        try:
            await websocket.close()
        except Exception:
            pass


def _decode_and_process(data: bytes, camera_id: int, pipeline) -> Optional[dict[str, Any]]:
    arr = np.frombuffer(data, np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        return None
    settings = get_settings()
    width = settings.STREAM_MAX_WIDTH
    if frame.shape[1] > width:
        scale = width / frame.shape[1]
        frame = cv2.resize(
            frame, (width, int(frame.shape[0] * scale)), interpolation=cv2.INTER_AREA
        )
    return pipeline.process_frame(frame, camera_id=camera_id)


def _encode_jpeg(frame: np.ndarray, quality: int) -> bytes:
    ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    return buf.tobytes() if ok else b""


@router.get("/{camera_id}/snapshot")
def stream_snapshot(camera_id: int, db: Session = Depends(get_db)):
    _camera(db, camera_id)
    jpeg = get_hub().snapshot(camera_id)
    if jpeg is None:
        raise HTTPException(status_code=404, detail="No live frame available")
    return Response(content=jpeg, media_type="image/jpeg")


@router.get("/{camera_id}/status")
def stream_status(camera_id: int, db: Session = Depends(get_db)):
    camera = _camera(db, camera_id)
    return {
        "camera_id": camera.id,
        "camera_name": camera.name,
        "streaming": bool(camera.is_streaming),
        "last_seen": camera.last_seen.isoformat() if camera.last_seen else None,
    }
