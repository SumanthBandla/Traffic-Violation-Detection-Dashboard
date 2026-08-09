"""Database engine, session factory and lightweight schema migration."""
from __future__ import annotations

import logging
import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db import models

logger = logging.getLogger("app.db")

engine = None
SessionLocal: sessionmaker = None  # type: ignore


def _build_engine() -> None:
    global engine, SessionLocal
    settings = get_settings()
    connect_args = {}
    if settings.DATABASE_URL.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        # Ensure the database file lives next to the backend when relative.
        if not settings.DATABASE_URL.startswith("sqlite:///"):
            settings.DATABASE_URL = "sqlite:///./traffic.db"
        db_path = settings.DATABASE_URL.replace("sqlite:///", "")
        parent = os.path.dirname(os.path.abspath(db_path))
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args=connect_args,
        pool_pre_ping=True,
        pool_recycle=3600,
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)


def ensure_schema() -> None:
    """Create tables if missing and add mobile-camera columns to legacy DBs."""
    if engine is None:
        _build_engine()

    models.Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    cameras_columns = {col["name"] for col in inspector.get_columns("cameras")}
    legacy_additions = {
        "camera_type": "VARCHAR(32) NOT NULL DEFAULT 'fixed'",
        "device_id": "VARCHAR(128)",
        "last_seen": "DATETIME",
        "is_streaming": "BOOLEAN NOT NULL DEFAULT 0",
    }
    for column, ddl in legacy_additions.items():
        if column not in cameras_columns:
            logger.info("Adding missing cameras column %s", column)
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE cameras ADD COLUMN {column} {ddl}"))
    logger.info("Database schema ready at %s", get_settings().DATABASE_URL)


def get_db():
    """FastAPI dependency yielding a database session."""
    if SessionLocal is None:
        _build_engine()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_session():
    """Create an independent session (safe to call from worker threads)."""
    if SessionLocal is None:
        _build_engine()
    return SessionLocal()


def init_db() -> None:
    ensure_schema()
