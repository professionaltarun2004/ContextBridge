"""
Integration tests for the sync and context API endpoints.
Uses mocked Auth0 JWT verification and mocked LiteLLM calls.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthTokenClaims, require_subscription
from app.main import app


def _make_auth_override(sub: str, email: str, subscribed: bool) -> AuthTokenClaims:
    claims = AuthTokenClaims.__new__(AuthTokenClaims)
    claims.sub = sub
    claims.email = email
    claims.raw = {}
    return claims


class TestSyncEndpoint:
    """Tests for POST /api/v1/sync."""

    @pytest.mark.asyncio
    async def test_sync_requires_auth(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/sync",
            json={
                "source_platform": "chatgpt",
                "messages": [
                    {"role": "user", "text": "Hello", "timestamp": "2024-01-01T00:00:00Z"}
                ],
            },
        )
        # Without auth override, should get 401 or 403
        assert response.status_code in (401, 403, 422)

    @pytest.mark.asyncio
    async def test_sync_returns_summary(self, client: AsyncClient, test_db: AsyncSession) -> None:
        """Full sync flow with mocked LiteLLM and auth."""
        mock_auth = _make_auth_override("auth0|paid", "paid@test.com", True)

        with (
            patch("app.routers.sync.require_subscription", return_value=mock_auth),
            patch(
                "app.routers.sync.generate_summary",
                new_callable=AsyncMock,
                return_value="Mocked summary: user asked about Python async.",
            ),
            patch(
                "app.routers.sync.generate_embeddings",
                new_callable=AsyncMock,
                return_value=[0.1] * 1536,
            ),
        ):
            app.dependency_overrides[require_subscription] = lambda: mock_auth

            response = await client.post(
                "/api/v1/sync",
                json={
                    "source_platform": "claude",
                    "messages": [
                        {
                            "role": "user",
                            "text": "How do I use async/await in Python?",
                            "timestamp": "2024-01-01T00:00:00Z",
                        },
                        {
                            "role": "assistant",
                            "text": "You define async functions with `async def`.",
                            "timestamp": "2024-01-01T00:00:01Z",
                        },
                    ],
                    "preset": "code_logic",
                },
                headers={"Authorization": "Bearer fake_token"},
            )

        app.dependency_overrides.clear()
        assert response.status_code == 201
        data = response.json()
        assert "conversation_id" in data
        assert "summary_text" in data
        assert data["preset_applied"] == "code_logic"
        assert "Mocked summary" in data["summary_text"]

    @pytest.mark.asyncio
    async def test_sync_invalid_platform_returns_422(
        self, client: AsyncClient
    ) -> None:
        mock_auth = _make_auth_override("auth0|paid", "paid@test.com", True)
        app.dependency_overrides[require_subscription] = lambda: mock_auth

        response = await client.post(
            "/api/v1/sync",
            json={
                "source_platform": "twitter",
                "messages": [
                    {"role": "user", "text": "Hello", "timestamp": "2024-01-01T00:00:00Z"}
                ],
            },
            headers={"Authorization": "Bearer fake_token"},
        )

        app.dependency_overrides.clear()
        assert response.status_code == 422


class TestTelemetryEndpoint:
    """Tests for POST /api/v1/telemetry/scraper-error."""

    @pytest.mark.asyncio
    async def test_valid_telemetry_returns_201(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/telemetry/scraper-error",
            json={
                "platform": "chatgpt",
                "targetURL": "https://chatgpt.com/c/abc123",
                "errorLog": "No conversation turns found. DOM selector may have changed.",
                "domStructureSnippet": "<main> <div.react-scroll-to-bottom>",
            },
        )
        assert response.status_code == 201
        assert response.json()["status"] == "received"

    @pytest.mark.asyncio
    async def test_telemetry_missing_error_log_returns_422(
        self, client: AsyncClient
    ) -> None:
        response = await client.post(
            "/api/v1/telemetry/scraper-error",
            json={
                "platform": "claude",
                "targetURL": "https://claude.ai",
                "errorLog": "",  # min_length=1
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_telemetry_missing_platform_returns_422(
        self, client: AsyncClient
    ) -> None:
        response = await client.post(
            "/api/v1/telemetry/scraper-error",
            json={
                "targetURL": "https://claude.ai",
                "errorLog": "Error message here",
            },
        )
        assert response.status_code == 422


class TestHealthCheck:
    """Tests for GET /health."""

    @pytest.mark.asyncio
    async def test_health_returns_200(self, client: AsyncClient) -> None:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
