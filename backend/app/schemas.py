"""
Pydantic request/response schemas for ContextBridge API.
Enforces strict schema validation on all incoming/outgoing payloads.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class MessageRole(str, Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class MessageSchema(BaseModel):
    role: MessageRole
    text: str = Field(..., min_length=1, max_length=50_000)
    timestamp: str = Field(..., description="ISO 8601 timestamp")

    @field_validator("text")
    @classmethod
    def text_must_not_contain_raw_secrets(cls, v: str) -> str:
        """
        Server-side PII leak scan — ensures raw API keys/tokens don't
        survive in incoming sync requests. (Solution: Input Validation)
        """
        import re

        dangerous_patterns = [
            r"sk-[A-Za-z0-9]{32,}",
            r"sk-ant-[A-Za-z0-9\-_]{32,}",
            r"AKIA[A-Z0-9]{16}",
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, v):
                # Mask rather than reject — client sanitizer should have caught this
                import re as _re
                v = _re.sub(pattern, "[SERVER_REDACTED]", v)
        return v


class SummarizationPreset(str, Enum):
    code_logic = "code_logic"
    conversational = "conversational"
    ultra_dense = "ultra_dense"


# ---------------------------------------------------------------------------
# /api/v1/sync
# ---------------------------------------------------------------------------


class SyncRequestPayload(BaseModel):
    source_platform: str = Field(
        ...,
        pattern=r"^(chatgpt|claude|gemini|local)$",
        description="Originating AI platform identifier",
    )
    messages: list[MessageSchema] = Field(
        ..., min_length=1, max_length=500, description="Sanitized message list"
    )
    preset: SummarizationPreset = SummarizationPreset.conversational


class SyncResponsePayload(BaseModel):
    conversation_id: str
    summary_text: str
    preset_applied: str


# ---------------------------------------------------------------------------
# /api/v1/context
# ---------------------------------------------------------------------------


class ContextMatch(BaseModel):
    chunk_id: str
    summary_text: str
    similarity_score: float


class MatchContextResponse(BaseModel):
    matches: list[ContextMatch]


# ---------------------------------------------------------------------------
# /api/v1/telemetry/scraper-error
# ---------------------------------------------------------------------------


class TelemetryErrorPayload(BaseModel):
    platform: str = Field(..., min_length=1, max_length=50)
    target_url: str = Field(..., alias="targetURL")
    error_log: str = Field(..., min_length=1, alias="errorLog")
    dom_structure_snippet: str = Field(alias="domStructureSnippet", default="")

    model_config = {"populate_by_name": True}


class TelemetryResponse(BaseModel):
    status: str = "received"


# ---------------------------------------------------------------------------
# /api/v1/stripe/webhook
# ---------------------------------------------------------------------------


class StripeWebhookResponse(BaseModel):
    status: str = "processed"


# ---------------------------------------------------------------------------
# Generic error response
# ---------------------------------------------------------------------------


class ErrorResponse(BaseModel):
    detail: str
    code: str | None = None
    meta: dict[str, Any] | None = None
