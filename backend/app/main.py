"""FastAPI application entry point for Repo-convert.

Starts the app, configures CORS, mounts API routes, and registers
startup / shutdown lifecycle hooks via the ASGI lifespan context manager.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.services import job_service

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CORS origins (resolved once at import time)
# ---------------------------------------------------------------------------

_raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
)
_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

if "*" in _origins:
    raise ValueError(
        "ALLOWED_ORIGINS='*' is not allowed when CORS allow_credentials=True. "
        "Set ALLOWED_ORIGINS to a comma-separated list of explicit origins."
    )


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def _lifespan(application: FastAPI):
    """Manage startup and shutdown tasks for the application.

    Yields control to FastAPI while the application is running, then
    cleans up all in-flight job working directories on shutdown.
    """
    logger.info("Repo-convert API started (allowed origins: %s)", _origins)
    yield
    logger.info("Shutting down — cleaning up job working directories.")
    job_service.cleanup_all()


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Repo-convert API",
    description=(
        "Converts repository Markdown files into plain-text files compatible "
        "with Microsoft 365 Chat agents."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=_lifespan,
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

app.include_router(router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/health", tags=["Health"])
def health_check():
    """Simple liveness probe.

    Returns:
        ``{"status": "ok"}``
    """
    return {"status": "ok"}
