"""Rule-based violation engine.

The engine is deliberately conservative: a violation is only emitted when a
rule condition persists over a short confirmation window, and each violation
type is throttled per track/camera so we do not flood the database with
per-frame writes.
"""
from __future__ import annotations

import time
from typing import Any, Optional

SPEED_LIMIT_KMH = 60.0


class ViolationEngine:
    def __init__(
        self,
        speed_limit_kmh: float = SPEED_LIMIT_KMH,
        confirm_frames: int = 3,
        throttle_seconds: float = 30.0,
    ) -> None:
        self.speed_limit = speed_limit_kmh
        self._confirm: dict[str, int] = {}
        self._last_emit: dict[str, float] = {}
        self.confirm_frames = confirm_frames
        self.throttle_seconds = throttle_seconds

    def _persist(self, key: str) -> bool:
        now = time.monotonic()
        if now - self._last_emit.get(key, 0.0) < self.throttle_seconds:
            return False
        self._last_emit[key] = now
        return True

    def evaluate(
        self,
        detections: list[dict[str, Any]],
        camera_id: Optional[int],
    ) -> list[dict[str, Any]]:
        """Return list of violation events. Keys allow confirmation + throttle."""
        events: list[dict[str, Any]] = []
        for det in detections:
            if det["label"] not in {"car", "bus", "truck", "motorcycle", "bicycle"}:
                continue
            track_id = det["track_id"]
            key = f"c{camera_id or 0}:t{track_id}"

            if det.get("speed_kmh", 0.0) > self.speed_limit:
                self._confirm[key] = self._confirm.get(key, 0) + 1
                if self._confirm[key] >= self.confirm_frames and self._persist(key):
                    events.append(
                        {
                            "violation_type": "speeding",
                            "confidence": min(0.99, 0.5 + (det["speed_kmh"] - self.speed_limit) / 200),
                            "description": (
                                f"{det['label']} detected at {det['speed_kmh']:.0f} km/h "
                                f"(limit {self.speed_limit:.0f} km/h)"
                            ),
                            "track_id": track_id,
                            "bbox": det["bbox"],
                            "detection": det,
                        }
                    )
                    self._confirm[key] = 0
            else:
                self._confirm[key] = 0
        return events

    def reset(self) -> None:
        self._confirm.clear()
        self._last_emit.clear()
