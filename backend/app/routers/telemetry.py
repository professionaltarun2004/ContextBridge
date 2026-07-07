"""
POST /api/v1/telemetry/scraper-error
Receives DOM parsing failure payloads from client extensions.
NFR-003: Powers the proactive alert pipeline.
T15: No authentication required (optional JWT for enrichment).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request, status

from app.schemas import TelemetryErrorPayload, TelemetryResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/scraper-error",
    response_model=TelemetryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Report DOM scraper parse failure",
    description=(
        "Accepts structured diagnostic payloads from client extensions when "
        "a DOM selector fails on a target AI platform. Used to power the "
        "automated alert pipeline (NFR-003)."
    ),
)
async def report_scraper_error(
    payload: TelemetryErrorPayload,
    request: Request,
) -> TelemetryResponse:
    """
    Logs the scraper error in structured JSON format to stdout.
    In production, this feeds into Sentry and the GHA alert pipeline.
    """
    user_agent = request.headers.get("user-agent", "unknown")

    # Structured JSON log — feeds Sentry and log aggregation pipelines
    logger.error(
        "Scraper DOM failure",
        extra={
            "event": "scraper_error",
            "platform": payload.platform,
            "target_url": payload.target_url,
            "error_log": payload.error_log,
            "dom_snippet": payload.dom_structure_snippet[:500],
            "user_agent": user_agent,
        },
    )

    return TelemetryResponse(status="received")
