"""API router aggregation."""
from __future__ import annotations

from fastapi import APIRouter

from app.api import (
    auth,
    cameras,
    dashboard,
    detections,
    evidence,
    quantum,
    search,
    stream,
    violations,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(cameras.router)
api_router.include_router(violations.router)
api_router.include_router(evidence.router)
api_router.include_router(dashboard.router)
api_router.include_router(search.router)
api_router.include_router(detections.router)
api_router.include_router(stream.router)
api_router.include_router(quantum.router)
