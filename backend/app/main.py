"""FastAPI application entry point."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.db.session import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    logger.info(
        "Starting %s | AI_MODE=%s | DB=%s",
        settings.APP_NAME,
        settings.AI_MODE,
        settings.DATABASE_URL.split(":")[0],
    )
    init_db()
    yield


settings = get_settings()
app = FastAPI(
    title=settings.APP_NAME,
    version="2.0.0",
    description=(
        "Traffic Violation Detection backend. Serves the React dashboard and "
        "acts as the streaming/AI hub for the mobile camera client."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME}


@app.get("/")
def root():
    return {
        "app": settings.APP_NAME,
        "docs": "/docs",
        "api": settings.API_V1_PREFIX,
        "mobile_integration": {
            "ingest": "/api/v1/stream/{camera_id}/ingest",
            "live": "/api/v1/detections/live",
            "register": "/api/v1/cameras",
        },
    }
