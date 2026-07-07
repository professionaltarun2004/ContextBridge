"""
ContextBridge FastAPI Application Entry Point.
Configures CORS, middleware, routing, startup/shutdown lifecycle, and Sentry.
"""

from __future__ import annotations

import logging
import logging.config
import uuid
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.purge_daemon import start_purge_scheduler, stop_purge_scheduler
from app.routers import stripe_webhook, sync, telemetry

# ---------------------------------------------------------------------------
# Logging — Structured JSON to stdout
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format=(
        '{"time": "%(asctime)s", "level": "%(levelname)s"'
        ', "logger": "%(name)s", "message": "%(message)s"}'
    ),
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sentry — Optional error collection (NFR telemetry)
# ---------------------------------------------------------------------------

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.APP_ENV,
        traces_sample_rate=0.1,
    )
    logger.info("Sentry initialized with DSN (env=%s)", settings.APP_ENV)


# ---------------------------------------------------------------------------
# Application Lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("ContextBridge backend starting up (env=%s)...", settings.APP_ENV)
    start_purge_scheduler()
    yield
    logger.info("ContextBridge backend shutting down...")
    stop_purge_scheduler()


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="ContextBridge API",
    description=(
        "SharedMemory AI — Cross-browser AI context synchronization platform. "
        "Captures, sanitizes, summarizes, and injects conversation context "
        "between AI assistants."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS — Only allow extension and known origins
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "x-request-id"],
    expose_headers=["x-request-id"],
)

# ---------------------------------------------------------------------------
# Request ID Middleware — Correlation tracing (Solution: Observability)
# ---------------------------------------------------------------------------

@app.middleware("http")
async def add_request_id(
    request: Request,
    call_next: Callable[[Request], Response],
) -> Response:
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    response = await call_next(request)  # type: ignore[arg-type]
    response.headers["x-request-id"] = request_id
    return response


# ---------------------------------------------------------------------------
# Global Exception Handler
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    logger.error(
        "Unhandled exception on %s %s: %s",
        request.method,
        request.url.path,
        exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred."},
    )


# ---------------------------------------------------------------------------
# API Routers
# ---------------------------------------------------------------------------

API_PREFIX = "/api/v1"

app.include_router(
    sync.router,
    prefix=API_PREFIX,
    tags=["Sync & Context"],
)

app.include_router(
    telemetry.router,
    prefix=f"{API_PREFIX}/telemetry",
    tags=["Telemetry"],
)

app.include_router(
    stripe_webhook.router,
    prefix=f"{API_PREFIX}/stripe",
    tags=["Billing"],
)


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["Health"])
async def health_check() -> dict:  # type: ignore[type-arg]
    return {"status": "healthy", "version": "0.1.0", "env": settings.APP_ENV}
