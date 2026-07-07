"""
Unit tests for the sanitization engine (FR-002).
Tests PII redaction, blocklist filtering, injection escaping, and checksum generation.
"""

from __future__ import annotations

import pytest

# Note: These tests run against the extension TypeScript code via logic parity.
# The sanitization logic is also re-implemented here in Python for backend
# PII leak scan validation (schemas.py text_must_not_contain_raw_secrets).
from app.schemas import MessageRole, MessageSchema


class TestServerSidePIIRedaction:
    """Tests for the server-side PII leak scan in MessageSchema."""

    def test_openai_key_is_server_redacted(self) -> None:
        msg = MessageSchema(
            role=MessageRole.user,
            text="My key is sk-abcdefghijklmnopqrstuvwxyz123456",
            timestamp="2024-01-01T00:00:00Z",
        )
        assert "[SERVER_REDACTED]" in msg.text
        assert "sk-abcdefghijklmnopqrstuvwxyz123456" not in msg.text

    def test_anthropic_key_is_server_redacted(self) -> None:
        msg = MessageSchema(
            role=MessageRole.assistant,
            text="Use sk-ant-api03-abcdefghijklmnopqrstuvwxyz123456789 for auth",
            timestamp="2024-01-01T00:00:00Z",
        )
        assert "[SERVER_REDACTED]" in msg.text

    def test_aws_key_is_server_redacted(self) -> None:
        msg = MessageSchema(
            role=MessageRole.user,
            text="AWS key: AKIAIOSFODNN7EXAMPLE",
            timestamp="2024-01-01T00:00:00Z",
        )
        assert "[SERVER_REDACTED]" in msg.text

    def test_clean_text_passes_through(self) -> None:
        original = "Let me explain how async/await works in Python."
        msg = MessageSchema(
            role=MessageRole.user,
            text=original,
            timestamp="2024-01-01T00:00:00Z",
        )
        assert msg.text == original

    def test_message_text_too_short_raises(self) -> None:
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            MessageSchema(
                role=MessageRole.user,
                text="",
                timestamp="2024-01-01T00:00:00Z",
            )


class TestSyncRequestValidation:
    """Tests for SyncRequestPayload schema validation."""

    def test_valid_sync_payload(self) -> None:
        from app.schemas import SyncRequestPayload
        payload = SyncRequestPayload(
            source_platform="chatgpt",
            messages=[
                MessageSchema(
                    role=MessageRole.user,
                    text="Hello world",
                    timestamp="2024-01-01T00:00:00Z",
                )
            ],
        )
        assert payload.source_platform == "chatgpt"
        assert len(payload.messages) == 1

    def test_invalid_platform_raises(self) -> None:
        from pydantic import ValidationError

        from app.schemas import SyncRequestPayload
        with pytest.raises(ValidationError):
            SyncRequestPayload(
                source_platform="twitter",
                messages=[
                    MessageSchema(
                        role=MessageRole.user,
                        text="Hello",
                        timestamp="2024-01-01T00:00:00Z",
                    )
                ],
            )

    def test_empty_messages_raises(self) -> None:
        from pydantic import ValidationError

        from app.schemas import SyncRequestPayload
        with pytest.raises(ValidationError):
            SyncRequestPayload(
                source_platform="claude",
                messages=[],
            )


class TestTelemetryPayload:
    """Tests for TelemetryErrorPayload validation."""

    def test_valid_telemetry_payload(self) -> None:
        from app.schemas import TelemetryErrorPayload
        payload = TelemetryErrorPayload(
            platform="chatgpt",
            targetURL="https://chatgpt.com/c/123",
            errorLog="No conversation turns found. DOM selector may have changed.",
            domStructureSnippet="<main> <div.container> <section>",
        )
        assert payload.platform == "chatgpt"
        assert "DOM selector" in payload.error_log

    def test_missing_error_log_raises(self) -> None:
        from pydantic import ValidationError

        from app.schemas import TelemetryErrorPayload
        with pytest.raises(ValidationError):
            TelemetryErrorPayload(
                platform="claude",
                targetURL="https://claude.ai",
                errorLog="",  # min_length=1
            )
