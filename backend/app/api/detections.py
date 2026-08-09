"""Live detections WebSocket channel for the dashboard.

The dashboard connects once and receives:

* ``frame`` events only for cameras it subscribed to (via ``subscribe`` control)
* ``detection`` / ``violation`` / ``camera_status`` events for all cameras

Auth is via ``?token=<jwt>``. Viewers require an ``admin`` or ``officer`` role.
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException
from starlette.websockets import WebSocket, WebSocketDisconnect

from app.api.deps import resolve_token
from app.stream.hub import get_hub

logger = logging.getLogger("app.api.detections")
router = APIRouter(prefix="/detections", tags=["detections"])

VIEWER_ROLES = {"admin", "officer"}


@router.websocket("/live")
async def live_detections(websocket: WebSocket):
    token = websocket.query_params.get("token")
    user = resolve_token(token)
    if user is None or user.role not in VIEWER_ROLES:
        await websocket.close(code=4403)
        return

    await websocket.accept()
    hub = get_hub()
    viewer = await hub.add_viewer(websocket)

    try:
        await websocket.send_text(
            json.dumps(
                {
                    "type": "hello",
                    "message": "live detections channel connected",
                    "role": user.role,
                }
            )
        )
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break
            if message["type"] != "websocket.receive":
                continue
            text = message.get("text")
            if not text:
                continue
            try:
                control = json.loads(text)
            except json.JSONDecodeError:
                continue
            action = control.get("type")
            camera_id = control.get("camera_id")
            if action == "subscribe":
                await hub.subscribe(websocket, camera_id)
            elif action == "unsubscribe":
                await hub.unsubscribe(websocket, camera_id)
            elif action == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        pass
    finally:
        await hub.remove_viewer(websocket)
