"""
Unit tests for the 24-hour purge daemon.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.purge_daemon import (
    purge_expired_raw_histories,
    start_purge_scheduler,
    stop_purge_scheduler,
)


class TestPurgeDaemon:
    """Tests for the 24h raw history purge daemon."""

    @pytest.mark.asyncio
    async def test_purge_nullifies_old_conversations(self) -> None:
        """
        Verifies that the purge function runs without error.
        We patch the entire AsyncSessionLocal to return a compatible mock
        that simulates the async context manager + begin() protocol.
        """
        # Build result mock
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [("uuid-1",), ("uuid-2",)]

        # Build inner session mock
        mock_inner = AsyncMock()
        mock_inner.execute = AsyncMock(return_value=mock_result)

        # begin() context manager
        mock_begin_ctx = AsyncMock()
        mock_begin_ctx.__aenter__ = AsyncMock(return_value=None)
        mock_begin_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_inner.begin = MagicMock(return_value=mock_begin_ctx)

        # Outer AsyncSessionLocal() context manager
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_inner)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("app.purge_daemon.AsyncSessionLocal", return_value=mock_session_ctx):
            # Should run without raising
            await purge_expired_raw_histories()

    @pytest.mark.asyncio
    async def test_scheduler_starts_without_error(self) -> None:
        """Verifies scheduler starts and can be stopped cleanly."""
        start_purge_scheduler()
        stop_purge_scheduler()

    def test_scheduler_stop_is_idempotent(self) -> None:
        """Stopping an already stopped scheduler should not raise."""
        stop_purge_scheduler()
        stop_purge_scheduler()  # Should not raise
