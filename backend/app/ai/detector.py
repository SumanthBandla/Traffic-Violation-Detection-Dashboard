"""Object detection abstraction.

``AI_MODE=live`` uses Ultralytics YOLO when model weights are available.
``AI_MODE=demo`` (default) produces deterministic synthetic detections so the
full streaming/violation pipeline works without model weights.
"""
from __future__ import annotations

import logging
import random
import threading
from typing import Any, Optional

import cv2
import numpy as np

from app.core.config import get_settings

logger = logging.getLogger("app.ai.detector")

COCO_NAMES = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train",
    "truck", "boat", "traffic light", "fire hydrant", "stop sign",
    "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep",
    "cow", "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella",
]

VEHICLE_CLASSES = {"car", "bus", "truck", "motorcycle", "bicycle"}


class BaseDetector:
    def detect(self, frame: np.ndarray) -> list[dict[str, Any]]:
        """Return detections: [{bbox: (x1,y1,x2,y2), confidence, class_id, label}]."""
        raise NotImplementedError


class DemoDetector(BaseDetector):
    """Deterministic synthetic detector used when AI_MODE=demo.

    Simulates a few vehicles moving through the frame so live monitoring,
    tracking, violations and quantum demand work end-to-end offline.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._agents: dict[str, dict[str, Any]] = {}
        self._frame_counter = 0

    def _reset_agents(self, width: int, height: int) -> None:
        agent_count = random.randint(2, 5)
        self._agents = {}
        for i in range(agent_count):
            # ~25% of demo agents intentionally speed so the violation engine
            # fires regularly during demo mode.
            speeding = random.random() < 0.25
            self._agents[f"demo_{i}"] = {
                "x": random.uniform(0.05, 0.95) * width,
                "y": random.uniform(0.15, 0.85) * height,
                "w": random.uniform(0.08, 0.16) * width,
                "h": random.uniform(0.09, 0.18) * height,
                "vx": random.choice([-1, 1]) * width * random.uniform(0.004, 0.014),
                "vy": random.uniform(0.002, 0.008) * height,
                "cls": random.choice(["car", "car", "car", "bus", "truck", "motorcycle"]),
                "speed": random.uniform(65, 110) if speeding else random.uniform(25, 55),
            }

    def detect(self, frame: np.ndarray) -> list[dict[str, Any]]:
        height, width = frame.shape[:2]
        with self._lock:
            self._frame_counter += 1
            if self._frame_counter % 90 == 0 or not self._agents:
                self._reset_agents(width, height)

            detections: list[dict[str, Any]] = []
            for agent_id, a in self._agents.items():
                a["x"] += a["vx"]
                a["y"] += a["vy"]
                if a["x"] < -a["w"] or a["x"] > width or a["y"] > height + a["h"]:
                    a["x"] = random.uniform(0.05, 0.9) * width
                    a["y"] = -a["h"]
                    a["vx"] = random.choice([-1, 1]) * width * random.uniform(0.004, 0.014)
                x1 = max(0.0, a["x"])
                y1 = max(0.0, a["y"])
                x2 = min(float(width), a["x"] + a["w"])
                y2 = min(float(height), a["y"] + a["h"])
                if x2 - x1 < 4 or y2 - y1 < 4:
                    continue
                conf = random.uniform(0.62, 0.94)
                detections.append(
                    {
                        "track_id": int(agent_id.split("_")[1]),
                        "bbox": [x1, y1, x2, y2],
                        "confidence": conf,
                        "class_id": COCO_NAMES.index(a["cls"]),
                        "label": a["cls"],
                        "speed_kmh": a["speed"],
                        "agent_id": agent_id,
                    }
                )
            return detections


class YoloDetector(BaseDetector):
    """Live YOLO detector (Ultralytics). Falls back to demo on load failure."""

    def __init__(self, model_path: str, conf_threshold: float) -> None:
        try:
            from ultralytics import YOLO  # type: ignore
        except ImportError as exc:  # pragma: no cover
            logger.warning("ultralytics not installed, falling back to demo: %s", exc)
            self._fallback = DemoDetector()
            self._model = None
            return
        self._model = YOLO(model_path)
        self._conf_threshold = conf_threshold
        self._fallback = None
        logger.info("Loaded YOLO model from %s", model_path)

    def detect(self, frame: np.ndarray) -> list[dict[str, Any]]:
        if self._model is None:
            return self._fallback.detect(frame)
        results = self._model.predict(
            frame, conf=self._conf_threshold, verbose=False, device="cpu"
        )
        detections: list[dict[str, Any]] = []
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                label = r.names.get(cls_id, "object")
                detections.append(
                    {
                        "track_id": -1,
                        "bbox": [x1, y1, x2, y2],
                        "confidence": conf,
                        "class_id": cls_id,
                        "label": label,
                        "speed_kmh": 0.0,
                        "agent_id": None,
                    }
                )
        return detections


def create_detector() -> BaseDetector:
    settings = get_settings()
    if settings.AI_MODE.lower() == "live":
        try:
            return YoloDetector(settings.YOLO_MODEL_PATH, settings.CONFIDENCE_THRESHOLD)
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.warning("Live detector failed to load (%s); using demo mode.", exc)
    return DemoDetector()
