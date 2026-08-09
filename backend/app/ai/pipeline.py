"""Detection pipeline: detect -> track -> evaluate violations -> annotate."""
from __future__ import annotations

import logging
import time
from typing import Any, Optional

import cv2
import numpy as np

from app.ai.detector import BaseDetector, VEHICLE_CLASSES, create_detector
from app.ai.tracker import IoUTracker
from app.ai.violation_engine import ViolationEngine

logger = logging.getLogger("app.ai.pipeline")

COLORS = {
    "car": (0, 200, 255),
    "bus": (0, 255, 200),
    "truck": (255, 170, 0),
    "motorcycle": (255, 0, 200),
    "bicycle": (120, 120, 255),
    "person": (0, 255, 0),
    "default": (255, 255, 255),
}


class Pipeline:
    def __init__(self) -> None:
        self.detector: BaseDetector = create_detector()
        self.tracker = IoUTracker()
        self.violations = ViolationEngine()
        self.frame_counter = 0

    def reset(self) -> None:
        self.tracker.reset()
        self.violations.reset()

    def process_frame(
        self,
        frame: np.ndarray,
        camera_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """Run the pipeline on a BGR frame.

        Returns detection summary plus an annotated copy of the frame.
        """
        start = time.monotonic()
        raw = self.detector.detect(frame)
        tracked = self.tracker.update(raw)
        events = self.violations.evaluate(tracked, camera_id)
        self.frame_counter += 1

        vehicle_count = sum(1 for d in tracked if d["label"] in VEHICLE_CLASSES)
        annotated = self._annotate(frame, tracked, events)

        return {
            "frame": annotated,
            "detections": tracked,
            "events": events,
            "vehicle_count": vehicle_count,
            "frame_number": self.frame_counter,
            "processing_ms": (time.monotonic() - start) * 1000,
        }

    @staticmethod
    def _annotate(
        frame: np.ndarray,
        detections: list[dict[str, Any]],
        events: list[dict[str, Any]],
    ) -> np.ndarray:
        for det in detections:
            x1, y1, x2, y2 = [int(v) for v in det["bbox"]]
            color = COLORS.get(det["label"], COLORS["default"])
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            label = f"{det['label']} {det['confidence']:.2f}"
            if det.get("speed_kmh", 0.0) > 0:
                label += f" {det['speed_kmh']:.0f}km/h"
            cv2.putText(
                frame, label, (x1, max(16, y1 - 6)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2, cv2.LINE_AA,
            )
        for ev in events:
            x1, y1, x2, y2 = [int(v) for v in ev["bbox"]]
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
            cv2.putText(
                frame, ev["violation_type"].upper(),
                (x1, min(frame.shape[0] - 10, y2 + 18)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA,
            )
        return frame


_pipeline: Optional[Pipeline] = None
_pipeline_lock = __import__("threading").Lock()
_camera_pipelines: dict[int, Pipeline] = {}


def get_pipeline(camera_id: Optional[int] = None) -> Pipeline:
    """Return a pipeline. When a camera id is provided a dedicated instance is
    used so tracking state is isolated per camera."""
    global _pipeline
    with _pipeline_lock:
        if camera_id is not None:
            if camera_id not in _camera_pipelines:
                _camera_pipelines[camera_id] = Pipeline()
            return _camera_pipelines[camera_id]
        if _pipeline is None:
            _pipeline = Pipeline()
        return _pipeline
