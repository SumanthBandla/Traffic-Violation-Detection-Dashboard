"""In-memory real-time hub connecting mobile camera ingest to dashboard viewers.

Two WebSocket channels are bridged here:

* **Ingest**  - ``/api/v1/stream/{camera_id}/ingest`` (mobile phone sends JPEG frames)
* **Viewer**  - ``/api/v1/detections/live`` (dashboard receives annotated frames,
  detections, violations and camera status events)

Frames are only forwarded to viewers that subscribed to that camera, keeping
bandwidth proportional to the number of cameras being watched.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from starlette.websockets import WebSocket

logger = logging.getLogger("app.stream.hub")


@dataclass
class Viewer:
    websocket: WebSocket
    subscriptions: set[int] = field(default_factory=set)


@dataclass
class LatestFrame:
    camera_id: int
    camera_name: str
    jpeg: bytes
    vehicle_count: int
    timestamp: float


class StreamHub:
    """Thread-safe-asyncio broadcast hub."""

    def __init__(self) -> None:
        self._viewers: dict[WebSocket, Viewer] = {}
        self._ingest_active: set[int] = set()
        self._latest: dict[int, LatestFrame] = {}
        self._lock = asyncio.Lock()

    # --- Viewer side (dashboard) ---
    async def add_viewer(self, websocket: WebSocket) -> Viewer:
        viewer = Viewer(websocket=websocket)
        async with self._lock:
            self._viewers[websocket] = viewer
        return viewer

    async def remove_viewer(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._viewers.pop(websocket, None)

    async def subscribe(self, websocket: WebSocket, camera_id: Optional[int]) -> None:
        async with self._lock:
            viewer = self._viewers.get(websocket)
            if viewer is None:
                return
            if camera_id is None:
                viewer.subscriptions = set()
            else:
                viewer.subscriptions.add(camera_id)

    async def unsubscribe(self, websocket: WebSocket, camera_id: Optional[int]) -> None:
        async with self._lock:
            viewer = self._viewers.get(websocket)
            if viewer is None:
                return
            if camera_id is None:
                viewer.subscriptions = set()
            else:
                viewer.subscriptions.discard(camera_id)

    # --- Ingest side (mobile) ---
    def mark_streaming(self, camera_id: int, streaming: bool) -> None:
        if streaming:
            self._ingest_active.add(camera_id)
        else:
            self._ingest_active.discard(camera_id)

    def is_streaming(self, camera_id: int) -> bool:
        return camera_id in self._ingest_active

    def get_latest_frame(self, camera_id: int) -> Optional[LatestFrame]:
        return self._latest.get(camera_id)

    async def publish_frame(
        self,
        camera_id: int,
        camera_name: str,
        jpeg: bytes,
        vehicle_count: int,
    ) -> None:
        frame = LatestFrame(
            camera_id=camera_id,
            camera_name=camera_name,
            jpeg=jpeg,
            vehicle_count=vehicle_count,
            timestamp=asyncio.get_event_loop().time(),
        )
        self._latest[camera_id] = frame
        await self.broadcast(
            {
                "type": "frame",
                "camera_id": camera_id,
                "camera_name": camera_name,
                "vehicle_count": vehicle_count,
                "image": _b64(jpeg),
                "ts": frame.timestamp,
            },
            only_subscribed_to=camera_id,
        )

    async def publish_event(self, message: dict[str, Any]) -> None:
        """Broadcast a structured event (detection/violation/status) to all viewers."""
        await self.broadcast(message)

    async def broadcast(self, message: dict[str, Any], only_subscribed_to: Optional[int] = None) -> None:
        async with self._lock:
            targets = [
                v.websocket
                for v in self._viewers.values()
                if only_subscribed_to is None
                or only_subscribed_to in v.subscriptions
                or not v.subscriptions
            ]
        if not targets:
            return
        import json

        payload = json.dumps(message, default=str)
        stale: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_text(payload)
            except Exception as exc:  # pragma: no cover - client went away
                logger.warning("viewer send failed: %s", exc)
                stale.append(ws)
        for ws in stale:
            await self.remove_viewer(ws)

    def snapshot(self, camera_id: int) -> Optional[bytes]:
        latest = self._latest.get(camera_id)
        return latest.jpeg if latest else None


def _b64(data: bytes) -> str:
    import base64

    return base64.b64encode(data).decode("ascii")


_hub: Optional[StreamHub] = None
_hub_lock = __import__("threading").Lock()


def get_hub() -> StreamHub:
    global _hub
    with _hub_lock:
        if _hub is None:
            _hub = StreamHub()
        return _hub
