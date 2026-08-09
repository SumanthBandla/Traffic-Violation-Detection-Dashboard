"""Pydantic schemas shared across routers."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Auth ---
class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=128)


class UserOut(ORMModel):
    id: int
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# --- Cameras ---
class CameraCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    location: str = Field("", max_length=255)
    lane_number: int = 1
    latitude: float = 0.0
    longitude: float = 0.0
    stream_url: str = Field("", max_length=512)
    camera_type: str = "fixed"  # fixed | mobile
    device_id: Optional[str] = Field(None, max_length=128)
    device_info: Optional[dict[str, Any]] = None


class CameraUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=128)
    location: Optional[str] = Field(None, max_length=255)
    lane_number: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    status: Optional[str] = None
    stream_url: Optional[str] = Field(None, max_length=512)
    camera_type: Optional[str] = None
    device_id: Optional[str] = Field(None, max_length=128)
    is_streaming: Optional[bool] = None


class CameraOut(ORMModel):
    id: int
    name: str
    location: str
    lane_number: int
    latitude: float
    longitude: float
    stream_url: str
    status: str
    camera_type: str
    device_id: Optional[str]
    last_seen: Optional[datetime]
    is_streaming: bool
    created_at: datetime


class CameraHeartbeat(BaseModel):
    status: str = "online"
    fps: float = 0.0
    battery: Optional[int] = Field(None, ge=0, le=100)
    network: str = "unknown"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    gps_accuracy: Optional[float] = None
    is_streaming: Optional[bool] = None


class CameraStreamStatus(BaseModel):
    is_streaming: bool


# --- Violations ---
class ViolationCreate(BaseModel):
    violation_type: str
    description: str = ""
    confidence: float = 0.0
    status: str = "pending"
    camera_id: Optional[int] = None
    vehicle_id: Optional[int] = None
    lane_number: int = 1
    location: str = ""
    detected_at: Optional[datetime] = None


class EvidenceOut(ORMModel):
    id: int
    violation_id_fk: Optional[int]
    kind: str
    path: str
    mime_type: str
    encrypted: bool
    captured_at: datetime


class ViolationOut(ORMModel):
    id: int
    violation_id: str
    violation_type: str
    description: str
    confidence: float
    status: str
    camera_id: Optional[int]
    vehicle_id: Optional[int]
    lane_number: int
    location: str
    detected_at: datetime
    created_at: datetime
    camera: Optional[CameraOut] = None
    evidence: list[EvidenceOut] = []


# --- Detection / live ---
class DetectionOut(BaseModel):
    camera_id: Optional[int]
    frame_number: int
    timestamp: datetime
    vehicle_count: int
    detections: list[dict[str, Any]]


# --- Dashboard ---
class HeatmapPoint(BaseModel):
    lat: float
    lng: float
    value: int
    label: str = ""


# --- Quantum ---
class IntersectionPhase(BaseModel):
    name: str
    queue: int
    phase: str
    green: int
    fixed_cameras: list[str] = []
    mobile_cameras: list[str] = []
    vehicle_demand: str = "LOW"
