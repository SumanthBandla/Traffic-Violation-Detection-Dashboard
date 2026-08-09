"""SQLAlchemy ORM models.

The schema matches the committed ``traffic.db`` so the application can run
against the existing seeded SQLite database. Additional columns on
``cameras`` support mobile camera registration and health tracking; they are
added automatically for legacy databases by ``ensure_schema``.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(128), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="officer")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class Camera(Base):
    __tablename__ = "cameras"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    lane_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    latitude: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    longitude: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    stream_url: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="inactive")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    # --- Mobile camera support (added by ensure_schema for legacy DBs) ---
    camera_type: Mapped[str] = mapped_column(String(32), nullable=False, default="fixed")
    device_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    last_seen: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_streaming: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plate_number: Mapped[str] = mapped_column(String(32), nullable=False)
    vehicle_type: Mapped[str] = mapped_column(String(32), nullable=False, default="car")
    brand: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    model: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    color: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    owner_name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    registration_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    insurance_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    puc_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    resource: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class Violation(Base):
    __tablename__ = "violations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    violation_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    violation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    camera_id: Mapped[Optional[int]] = mapped_column(ForeignKey("cameras.id"), nullable=True)
    vehicle_id: Mapped[Optional[int]] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    lane_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    location: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    detected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    camera: Mapped[Optional[Camera]] = relationship("Camera", lazy="selectin")
    vehicle: Mapped[Optional[Vehicle]] = relationship("Vehicle", lazy="selectin")


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    violation_id_fk: Mapped[Optional[int]] = mapped_column(
        ForeignKey("violations.id"), nullable=True
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="frame")
    path: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False, default="image/jpeg")
    encrypted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class DetectionLog(Base):
    __tablename__ = "detection_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    violation_id_fk: Mapped[Optional[int]] = mapped_column(
        ForeignKey("violations.id"), nullable=True
    )
    track_id: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    object_type: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    bbox: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    speed_kmh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    direction: Mapped[str] = mapped_column(String(16), nullable=False, default="unknown")
    log_meta: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
