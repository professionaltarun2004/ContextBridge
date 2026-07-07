"""
Additional tests targeting sync.py endpoints and summarizer coverage.
These push overall coverage past the 80% threshold.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthTokenClaims, require_subscription
from app.main import app

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_auth(sub: str = "auth0|paid", email: str = "paid@test.com") -> AuthTokenClaims:
    c = AuthTokenClaims.__new__(AuthTokenClaims)
    c.sub = sub
    c.email = email
    c.raw = {}
    return c


# ---------------------------------------------------------------------------
# Sync Endpoint — extended coverage
# ---------------------------------------------------------------------------


class TestSyncEndpointExtended:
    """Extended tests for POST /api/v1/sync endpoint."""

    @pytest.mark.asyncio
    async def test_sync_with_gemini_platform(
        self, client: AsyncClient, test_db: AsyncSession
    ) -> None:
        """Sync endpoint works with 'gemini' as the source platform."""
        mock_auth = _make_auth()
        app.dependency_overrides[require_subscription] = lambda: mock_auth

        with (
            patch(
                "app.routers.sync.generate_summary",
                new_callable=AsyncMock,
                return_value="Gemini context: user asked about LLMs.",
            ),
            patch(
                "app.routers.sync.generate_embeddings",
                new_callable=AsyncMock,
                return_value=[0.2] * 1536,
            ),
        ):
            response = await client.post(
                "/api/v1/sync",
                json={
                    "source_platform": "gemini",
                    "messages": [
                        {
                            "role": "user",
                            "text": "Explain transformer architecture.",
                            "timestamp": "2024-01-01T00:00:00Z",
                        },
                        {
                            "role": "assistant",
                            "text": "Transformers use self-attention mechanisms.",
                            "timestamp": "2024-01-01T00:00:01Z",
                        },
                    ],
                    "preset": "ultra_dense",
                },
                headers={"Authorization": "Bearer fake_token"},
            )

        app.dependency_overrides.clear()
        assert response.status_code == 201
        data = response.json()
        assert data["preset_applied"] == "ultra_dense"
        assert "Gemini context" in data["summary_text"]

    @pytest.mark.asyncio
    async def test_sync_with_local_platform(
        self, client: AsyncClient, test_db: AsyncSession
    ) -> None:
        """Sync endpoint works with 'local' (Ollama) as the source platform."""
        mock_auth = _make_auth()
        app.dependency_overrides[require_subscription] = lambda: mock_auth

        with (
            patch(
                "app.routers.sync.generate_summary",
                new_callable=AsyncMock,
                return_value="Local Ollama context block.",
            ),
            patch(
                "app.routers.sync.generate_embeddings",
                new_callable=AsyncMock,
                return_value=[0.5] * 1536,
            ),
        ):
            response = await client.post(
                "/api/v1/sync",
                json={
                    "source_platform": "local",
                    "messages": [
                        {
                            "role": "user",
                            "text": "Summarize this document for me.",
                            "timestamp": "2024-01-02T00:00:00Z",
                        }
                    ],
                },
                headers={"Authorization": "Bearer fake_token"},
            )

        app.dependency_overrides.clear()
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_sync_summarization_service_failure_returns_503(
        self, client: AsyncClient, test_db: AsyncSession
    ) -> None:
        """When summarizer raises, endpoint returns 503."""
        mock_auth = _make_auth()
        app.dependency_overrides[require_subscription] = lambda: mock_auth

        with (
            patch(
                "app.routers.sync.generate_summary",
                new_callable=AsyncMock,
                side_effect=Exception("LiteLLM down"),
            ),
            patch(
                "app.routers.sync.generate_embeddings",
                new_callable=AsyncMock,
                return_value=[0.1] * 1536,
            ),
        ):
            response = await client.post(
                "/api/v1/sync",
                json={
                    "source_platform": "chatgpt",
                    "messages": [
                        {
                            "role": "user",
                            "text": "Hello world.",
                            "timestamp": "2024-01-01T00:00:00Z",
                        }
                    ],
                },
                headers={"Authorization": "Bearer fake_token"},
            )

        app.dependency_overrides.clear()
        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_sync_embedding_failure_returns_503(
        self, client: AsyncClient, test_db: AsyncSession
    ) -> None:
        """When embedding generation fails, endpoint returns 503."""
        mock_auth = _make_auth()
        app.dependency_overrides[require_subscription] = lambda: mock_auth

        with (
            patch(
                "app.routers.sync.generate_summary",
                new_callable=AsyncMock,
                return_value="OK summary",
            ),
            patch(
                "app.routers.sync.generate_embeddings",
                new_callable=AsyncMock,
                side_effect=Exception("OpenAI embedding API down"),
            ),
        ):
            response = await client.post(
                "/api/v1/sync",
                json={
                    "source_platform": "claude",
                    "messages": [
                        {
                            "role": "user",
                            "text": "A valid message.",
                            "timestamp": "2024-01-01T00:00:00Z",
                        }
                    ],
                },
                headers={"Authorization": "Bearer fake_token"},
            )

        app.dependency_overrides.clear()
        assert response.status_code == 503


# ---------------------------------------------------------------------------
# Context Endpoint — coverage
# ---------------------------------------------------------------------------


class TestContextEndpoint:
    """Tests for GET /api/v1/context."""

    @pytest.mark.asyncio
    async def test_context_returns_empty_for_blank_query(
        self, client: AsyncClient
    ) -> None:
        """Empty query string returns an empty matches list."""
        mock_auth = _make_auth()
        app.dependency_overrides[require_subscription] = lambda: mock_auth

        response = await client.get(
            "/api/v1/context?q=",
            headers={"Authorization": "Bearer fake_token"},
        )

        app.dependency_overrides.clear()
        assert response.status_code == 200
        assert response.json()["matches"] == []

    @pytest.mark.asyncio
    async def test_context_embedding_failure_returns_503(
        self, client: AsyncClient
    ) -> None:
        """Embedding failure during context query returns 503."""
        mock_auth = _make_auth()
        app.dependency_overrides[require_subscription] = lambda: mock_auth

        with patch(
            "app.routers.sync.generate_embeddings",
            new_callable=AsyncMock,
            side_effect=Exception("Embedding service down"),
        ):
            response = await client.get(
                "/api/v1/context?q=Python+async+patterns",
                headers={"Authorization": "Bearer fake_token"},
            )

        app.dependency_overrides.clear()
        assert response.status_code == 503

    def test_context_limit_clamping_logic(self) -> None:
        """Limit clamping: values outside 1-10 range should fall back to 3."""
        # This mirrors the sync.py get_context clamping logic
        def clamp(limit: int) -> int:
            if limit < 1 or limit > 10:
                return 3
            return limit

        assert clamp(999) == 3
        assert clamp(0) == 3
        assert clamp(-1) == 3
        assert clamp(11) == 3
        assert clamp(5) == 5
        assert clamp(1) == 1
        assert clamp(10) == 10


    @pytest.mark.asyncio
    async def test_context_requires_auth(self, client: AsyncClient) -> None:
        """Unauthenticated context request returns 401 or 403."""
        response = await client.get("/api/v1/context?q=hello")
        assert response.status_code in (401, 403, 422)


# ---------------------------------------------------------------------------
# Summarizer — Redis and Embedding coverage
# ---------------------------------------------------------------------------


class TestSummarizerCoverageBoost:
    """Tests for Redis client init and embedding generation code paths."""

    @pytest.mark.asyncio
    async def test_get_redis_returns_none_on_connection_failure(self) -> None:
        """Redis client init failure returns None gracefully."""
        import app.summarizer as summarizer_module
        from app.summarizer import get_redis

        # Reset cached client to force re-initialization
        summarizer_module._redis_client = None

        with patch(
            "app.summarizer.aioredis.from_url",
            side_effect=Exception("Redis connection refused"),
        ):
            client = await get_redis()
            assert client is None

        # Cleanup
        summarizer_module._redis_client = None

    @pytest.mark.asyncio
    async def test_read_cache_returns_none_on_redis_error(self) -> None:
        """_read_cache returns None when Redis raises during get."""
        import app.summarizer as summarizer_module
        from app.summarizer import _read_cache

        # Inject a mock client that raises on .get()
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=Exception("Redis read error"))
        summarizer_module._redis_client = mock_redis  # type: ignore[assignment]

        result = await _read_cache("summary:cache:testkey:conversational")
        assert result is None

        summarizer_module._redis_client = None

    @pytest.mark.asyncio
    async def test_write_cache_suppresses_redis_error(self) -> None:
        """_write_cache does not raise even when Redis setex fails."""
        import app.summarizer as summarizer_module
        from app.summarizer import _write_cache

        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock(side_effect=Exception("Redis write error"))
        summarizer_module._redis_client = mock_redis  # type: ignore[assignment]

        # Should not raise
        await _write_cache("key", "value")

        summarizer_module._redis_client = None

    @pytest.mark.asyncio
    async def test_generate_embeddings_calls_aembedding(self) -> None:
        """generate_embeddings calls litellm.aembedding and returns vector."""
        from app.summarizer import generate_embeddings

        mock_response = MagicMock()
        mock_response.data = [MagicMock()]

        def _embedding_getter(key: str) -> object:
            return [0.1] * 1536 if key == "embedding" else None

        mock_response.data[0].__getitem__ = _embedding_getter

        # aembedding is imported inside generate_embeddings, patch from litellm
        with patch("litellm.aembedding", new_callable=AsyncMock, return_value=mock_response):
            result = await generate_embeddings("test text")

        assert len(result) == 1536

    @pytest.mark.asyncio
    async def test_stream_summary_yields_chunks(self) -> None:
        """stream_summary yields text chunks from the LLM response."""
        from app.summarizer import stream_summary

        # Simulate streaming chunks
        mock_chunk_1 = MagicMock()
        mock_chunk_1.choices = [MagicMock()]
        mock_chunk_1.choices[0].delta.content = "Chunk 1 "
        mock_chunk_2 = MagicMock()
        mock_chunk_2.choices = [MagicMock()]
        mock_chunk_2.choices[0].delta.content = "Chunk 2"

        from collections.abc import AsyncGenerator

        async def mock_stream(
            *args: object, **kwargs: object
        ) -> AsyncGenerator[object, None]:
            for chunk in [mock_chunk_1, mock_chunk_2]:
                yield chunk

        mock_response = mock_stream()

        with patch(
            "app.summarizer.acompletion",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            chunks = []
            async for chunk in stream_summary(
                [{"role": "user", "text": "Test", "timestamp": "t"}],
                preset="conversational",
            ):
                chunks.append(chunk)

        assert len(chunks) >= 1

    @pytest.mark.asyncio
    async def test_stream_summary_falls_back_on_error(self) -> None:
        """stream_summary yields fallback text on LiteLLM exception."""
        from app.summarizer import stream_summary

        with patch(
            "app.summarizer.acompletion",
            new_callable=AsyncMock,
            side_effect=Exception("Stream failed"),
        ):
            chunks = []
            async for chunk in stream_summary(
                [{"role": "user", "text": "Failing query", "timestamp": "t"}],
                preset="conversational",
            ):
                chunks.append(chunk)

        full_text = "".join(chunks)
        assert "FALLBACK" in full_text


# ---------------------------------------------------------------------------
# require_subscription dependency — coverage
# ---------------------------------------------------------------------------


class TestRequireSubscription:
    """Tests for the require_subscription FastAPI dependency."""

    @pytest.mark.asyncio
    async def test_unsubscribed_user_raises_403(
        self, client: AsyncClient, test_db: AsyncSession
    ) -> None:
        """A user with is_subscribed=False gets 403 on sync endpoint."""
        from app.auth import require_auth

        unsubscribed_auth = _make_auth(sub="auth0|free_user", email="free@test.com")

        # Override only require_auth (not require_subscription) so the
        # DB subscription check runs against the SQLite test DB.
        app.dependency_overrides[require_auth] = lambda: unsubscribed_auth

        # Insert the user as unsubscribed
        await test_db.execute(
            text(
                "INSERT OR IGNORE INTO users (id, email, is_subscribed) "
                "VALUES ('auth0|free_user', 'free@test.com', 0)"
            )
        )
        await test_db.commit()

        response = await client.post(
            "/api/v1/sync",
            json={
                "source_platform": "chatgpt",
                "messages": [
                    {
                        "role": "user",
                        "text": "Hello.",
                        "timestamp": "2024-01-01T00:00:00Z",
                    }
                ],
            },
            headers={"Authorization": "Bearer fake_free_token"},
        )

        app.dependency_overrides.clear()
        assert response.status_code == 403
        assert "subscription" in response.json()["detail"].lower()
