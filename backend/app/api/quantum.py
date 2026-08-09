"""Quantum-inspired traffic signal control (simulation / decision support).

This is a simulation only. It never talks to real traffic lights: operators
review and approve recommendations in the dashboard.
"""
from __future__ import annotations

import logging
import math
import threading
import time
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.db.models import Camera
from app.db.session import get_db
from app.api.deps import require_roles
from app.stream.hub import get_hub

logger = logging.getLogger("app.api.quantum")
router = APIRouter(prefix="/quantum", tags=["quantum"])

PHASES = ["NORTH_SOUTH", "EAST_WEST"]
MIN_GREEN, MAX_GREEN = 20, 60

INTERSECTION_NAMES = [
    "Intersection A",
    "Intersection B",
    "Intersection C",
    "Intersection D",
]


class IntersectionState:
    __slots__ = ("id", "name", "phase", "green", "queue", "locked_until")

    def __init__(self, idx: int, name: str) -> None:
        self.id = idx
        self.name = name
        self.phase = "NORTH_SOUTH"
        self.green = 30
        self.queue = 0
        self.locked_until = 0.0


class QuantumEngine:
    """Thread-safe in-memory signal state + quantum-inspired optimiser."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._intersections = [
            IntersectionState(i + 1, name) for i, name in enumerate(INTERSECTION_NAMES)
        ]

    def states(self) -> list[IntersectionState]:
        with self._lock:
            return list(self._intersections)

    def get(self, intersection_id: int) -> IntersectionState:
        for state in self._intersections:
            if state.id == intersection_id:
                return state
        raise KeyError(intersection_id)

    def optimise(self, intersection_id: int, queue: int, demand: str) -> dict[str, Any]:
        with self._lock:
            state = self.get(intersection_id)
            now = time.monotonic()
            state.queue = queue

            if now < state.locked_until:
                return {
                    "recommended_phase": state.phase,
                    "recommended_green": state.green,
                    "reason": "Phase locked (manual/pedestrian), waiting for approval window.",
                    "changed": False,
                }

            # Demand multiplier pushes the phase toward the busiest stream.
            demand_multiplier = {"LOW": 0.8, "MEDIUM": 1.0, "HIGH": 1.3}.get(
                demand.upper(), 1.0
            )
            scaled_queue = max(1, int(queue * demand_multiplier))

            recommended_phase = "EAST_WEST" if scaled_queue % 2 == 0 else "NORTH_SOUTH"
            green = min(MAX_GREEN, max(MIN_GREEN, scaled_queue + 12))

            changed = recommended_phase != state.phase or green != state.green
            if changed:
                state.phase = recommended_phase
                state.green = green
            return {
                "recommended_phase": recommended_phase,
                "recommended_green": green,
                "queue_estimate": queue,
                "demand": demand.upper(),
                "reason": (
                    "Quantum-inspired optimisation based on aggregated camera demand "
                    "and queue estimate."
                ),
                "changed": changed,
            }

    def set_phase(self, intersection_id: int, phase: str, lock_seconds: int = 15) -> dict[str, Any]:
        with self._lock:
            state = self.get(intersection_id)
            state.phase = phase.upper()
            state.green = 15 if phase.upper() in {"ALL_RED", "PEDESTRIAN"} else state.green
            state.locked_until = time.monotonic() + lock_seconds
            return {"phase": state.phase, "green": state.green, "locked_for": lock_seconds}


_engine: Optional[QuantumEngine] = None
_engine_lock = threading.Lock()


def get_engine() -> QuantumEngine:
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = QuantumEngine()
        return _engine


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * math.asin(math.sqrt(a)) * 6371.0


def _assign_cameras_to_intersections(db: Session) -> dict[int, list[Camera]]:
    """Assign cameras to the nearest seeded intersection by geodistance."""
    cameras = db.query(Camera).all()
    fixed = [c for c in cameras if c.camera_type != "mobile"][:4]
    if not fixed:
        fixed = cameras[:4]
    anchors = fixed or cameras[:4]

    buckets: dict[int, list[Camera]] = {i + 1: [] for i in range(len(anchors))}
    for camera in cameras:
        best_idx, best_dist = 0, float("inf")
        for idx, anchor in enumerate(anchors):
            dist = _haversine(
                camera.latitude, camera.longitude, anchor.latitude, anchor.longitude
            )
            if dist < best_dist:
                best_dist, best_idx = dist, idx
        buckets[best_idx + 1].append(camera)
    return buckets


def _demand_label(count: int) -> str:
    if count >= 24:
        return "HIGH"
    if count >= 12:
        return "MEDIUM"
    return "LOW"


@router.get("/overview")
def quantum_overview(db: Session = Depends(get_db)):
    engine = get_engine()
    hub = get_hub()
    buckets = _assign_cameras_to_intersections(db)

    total_vehicles = 0
    total_queue = 0
    fixed_active = mobile_active = 0
    for camera in db.query(Camera).all():
        if camera.camera_type == "mobile":
            if camera.status == "online" or camera.is_streaming:
                mobile_active += 1
        elif camera.status == "online":
            fixed_active += 1
        latest = hub.get_latest_frame(camera.id)
        count = latest.vehicle_count if latest else 0
        total_vehicles += count

    total_queue = int(total_vehicles * 0.5)
    estimated_delay = round(total_queue * 0.25, 1)

    intersections = []
    for state in engine.states():
        cam_list = buckets.get(state.id, [])
        fixed_names = [c.name for c in cam_list if c.camera_type != "mobile"]
        mobile_names = [c.name for c in cam_list if c.camera_type == "mobile"]
        queue = sum(
            (hub.get_latest_frame(c.id).vehicle_count if hub.get_latest_frame(c.id) else 0)
            * 2
            for c in cam_list
        )
        demand = _demand_label(queue)
        state.queue = queue
        intersections.append(
            {
                "id": state.id,
                "name": state.name,
                "phase": state.phase,
                "green": state.green,
                "queue": queue,
                "vehicle_demand": demand,
                "fixed_cameras": fixed_names,
                "mobile_cameras": mobile_names,
                "camera_sources": [c.name for c in cam_list],
                "optimised": engine.optimise(state.id, queue, demand)["recommended_phase"],
            }
        )

    return {
        "network_status": "online",
        "active_cameras": fixed_active + mobile_active,
        "fixed_cameras": fixed_active,
        "mobile_cameras": mobile_active,
        "total_vehicles": total_vehicles,
        "estimated_queue": total_queue,
        "estimated_delay_min": estimated_delay,
        "pending_safety_alerts": len(
            [c for c in db.query(Camera).all() if c.status not in {"online", "active"}]
        ),
        "intersections": intersections,
        "disclaimer": (
            "Simulation only. Do not connect this system directly to real-world "
            "traffic lights; recommendations require operator approval."
        ),
    }


@router.post("/intersections/{intersection_id}/optimise")
def optimise_intersection(
    intersection_id: int,
    user=Depends(require_roles("admin", "officer")),
    db: Session = Depends(get_db),
):
    engine = get_engine()
    hub = get_hub()
    buckets = _assign_cameras_to_intersections(db)
    cam_list = buckets.get(intersection_id, [])
    queue = sum(
        (hub.get_latest_frame(c.id).vehicle_count if hub.get_latest_frame(c.id) else 0) * 2
        for c in cam_list
    )
    demand = _demand_label(queue)
    try:
        result = engine.optimise(intersection_id, queue, demand)
    except KeyError:
        raise HTTPException(status_code=404, detail="Intersection not found")
    record_audit(
        db,
        actor=user.username,
        action="quantum_optimise",
        resource="intersection",
        resource_id=str(intersection_id),
        details=result,
    )
    result["intersection_id"] = intersection_id
    return result


@router.post("/intersections/{intersection_id}/phase/{phase}")
def set_intersection_phase(
    intersection_id: int,
    phase: str,
    user=Depends(require_roles("admin", "officer")),
    db: Session = Depends(get_db),
):
    engine = get_engine()
    phase = phase.upper()
    if phase not in {"NORTH_SOUTH", "EAST_WEST", "ALL_RED", "PEDESTRIAN"}:
        raise HTTPException(status_code=422, detail="Invalid phase")
    try:
        result = engine.set_phase(intersection_id, phase)
    except KeyError:
        raise HTTPException(status_code=404, detail="Intersection not found")
    record_audit(
        db,
        actor=user.username,
        action="quantum_phase",
        resource="intersection",
        resource_id=str(intersection_id),
        details={"phase": phase},
    )
    result["intersection_id"] = intersection_id
    return result
