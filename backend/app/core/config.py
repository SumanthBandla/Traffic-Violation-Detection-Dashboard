"""Application configuration loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the Traffic Violation Detection backend.

    All values can be overridden through environment variables, keeping
    secrets and deployment-specific configuration out of source code.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Application ---
    APP_NAME: str = "AI Traffic Violation Detection System"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # --- Security ---
    SECRET_KEY: str = "change-me-in-production-9f8a7b6c5d4e3f2a1b0c"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # --- Database ---
    DATABASE_URL: str = "sqlite:///./traffic.db"

    # --- Redis (optional; in-memory fallback) ---
    REDIS_URL: str = ""

    # --- AI ---
    AI_MODE: str = "demo"  # demo | live
    YOLO_MODEL_PATH: str = "weights/yolov11n.pt"
    CONFIDENCE_THRESHOLD: float = 0.35

    # --- Evidence ---
    EVIDENCE_DIR: str = "storage/evidence"
    ENCRYPT_EVIDENCE: bool = False
    EVIDENCE_RETENTION_DAYS: int = 180

    # --- Streaming / live detections ---
    STREAM_MAX_FPS: int = 15
    STREAM_MAX_WIDTH: int = 960
    STREAM_QUALITY: int = 80
    HEALTH_STALE_AFTER_SECONDS: int = 30

    # --- CORS ---
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:4173",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):  # noqa: N805
        if isinstance(v, str):
            cleaned = v.strip()
            if cleaned.startswith("["):
                import json

                return json.loads(cleaned)
            return [o.strip() for o in cleaned.split(",") if o.strip()]
        return v

    @property
    def secret_key(self) -> bytes:
        return self.SECRET_KEY.encode("utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
