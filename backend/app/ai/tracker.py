"""Lightweight IoU-based tracker that assigns persistent track ids."""
from __future__ import annotations

from typing import Any

import numpy as np


def _iou(a: list[float], b: list[float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw = max(0.0, ix2 - ix1)
    ih = max(0.0, iy2 - iy1)
    inter = iw * ih
    area_a = max(0.0, (ax2 - ax1) * (ay2 - ay1))
    area_b = max(0.0, (bx2 - bx1) * (by2 - by1))
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


class IoUTracker:
    """Simple greedy IoU tracker tolerant of short occlusion."""

    def __init__(self, iou_threshold: float = 0.2, max_age: int = 20) -> None:
        self._iou_threshold = iou_threshold
        self._max_age = max_age
        self._tracks: dict[int, dict[str, Any]] = {}
        self._next_id = 0

    def update(self, detections: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Associate detections to tracks and return tracks with stable ids."""
        for tid in self._tracks:
            self._tracks[tid]["age"] += 1

        assigned: set[int] = set()
        for det in detections:
            best_tid = None
            best_iou = self._iou_threshold
            det_box = det["bbox"]
            for tid, track in self._tracks.items():
                if tid in assigned:
                    continue
                score = _iou(det_box, track["bbox"])
                if score > best_iou:
                    best_iou = score
                    best_tid = tid
            if best_tid is not None:
                assigned.add(best_tid)
                self._tracks[best_tid].update(
                    {"bbox": det_box, "label": det["label"], "conf": det["confidence"],
                     "age": 0, "speed": det.get("speed_kmh", 0.0)}
                )
                det["track_id"] = best_tid
            else:
                track_id = self._next_id
                self._next_id += 1
                self._tracks[track_id] = {
                    "bbox": det_box, "label": det["label"], "conf": det["confidence"],
                    "age": 0, "speed": det.get("speed_kmh", 0.0),
                }
                det["track_id"] = track_id

        expired = [tid for tid, t in self._tracks.items() if t["age"] > self._max_age]
        for tid in expired:
            del self._tracks[tid]

        for det in detections:
            det["bbox"] = [float(v) for v in det["bbox"]]
        return detections

    def reset(self) -> None:
        self._tracks.clear()
        self._next_id = 0
