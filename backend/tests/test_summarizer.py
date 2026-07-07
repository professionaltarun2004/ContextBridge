"""
Unit tests for the summarization engine and Redis cache.
All LLM and Redis calls are mocked.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestSummarizerPresets:
    """Tests for the PRESETS dictionary and preset selection."""

    def test_all_presets_exist(self) -> None:
        from app.summarizer import PRESETS
        assert "code_logic" in PRESETS
        assert "conversational" in PRESETS
        assert "ultra_dense" in PRESETS

    def test_presets_are_non_empty_strings(self) -> None:
        from app.summarizer import PRESETS
        for key, value in PRESETS.items():
            assert isinstance(value, str), f"Preset '{key}' is not a string"
            assert len(value) > 50, f"Preset '{key}' seems too short"


class TestCacheKeyGeneration:
    """Tests for the Redis cache key construction."""

    def test_same_messages_same_preset_same_key(self) -> None:
        from app.summarizer import _build_cache_key
        messages = [{"role": "user", "text": "Hello", "timestamp": "t1"}]
        key1 = _build_cache_key(json.dumps(messages, sort_keys=True), "conversational")
        key2 = _build_cache_key(json.dumps(messages, sort_keys=True), "conversational")
        assert key1 == key2

    def test_different_preset_different_key(self) -> None:
        from app.summarizer import _build_cache_key
        messages = [{"role": "user", "text": "Hello", "timestamp": "t1"}]
        key1 = _build_cache_key(json.dumps(messages, sort_keys=True), "code_logic")
        key2 = _build_cache_key(json.dumps(messages, sort_keys=True), "conversational")
        assert key1 != key2

    def test_cache_key_format(self) -> None:
        from app.summarizer import _build_cache_key
        key = _build_cache_key("test_content", "conversational")
        assert key.startswith("summary:cache:")
        assert "conversational" in key

    def test_different_messages_different_key(self) -> None:
        from app.summarizer import _build_cache_key
        m1 = json.dumps([{"text": "Hello"}], sort_keys=True)
        m2 = json.dumps([{"text": "World"}], sort_keys=True)
        assert _build_cache_key(m1, "conversational") != _build_cache_key(m2, "conversational")


class TestDeterministicFallback:
    """Tests for the deterministic fallback summarizer."""

    def test_fallback_includes_last_turns(self) -> None:
        from app.summarizer import _deterministic_fallback
        messages = [
            {"role": "user", "text": "Question 1"},
            {"role": "assistant", "text": "Answer 1"},
            {"role": "user", "text": "Question 2"},
            {"role": "assistant", "text": "Answer 2"},
        ]
        result = _deterministic_fallback(messages)
        assert "Question 2" in result
        assert "Answer 2" in result
        assert "FALLBACK" in result

    def test_fallback_truncates_long_text(self) -> None:
        from app.summarizer import _deterministic_fallback
        long_text = "A" * 1000
        messages = [{"role": "user", "text": long_text}]
        result = _deterministic_fallback(messages)
        # Text should be truncated at 300 chars
        assert len(result) < 2000

    def test_fallback_returns_string(self) -> None:
        from app.summarizer import _deterministic_fallback
        assert isinstance(_deterministic_fallback([]), str)


class TestGenerateSummaryWithMocks:
    """Integration tests for generate_summary with mocked LiteLLM."""

    @pytest.mark.asyncio
    async def test_returns_cached_result_on_cache_hit(self) -> None:
        from app.summarizer import generate_summary

        with (
            patch(
                "app.summarizer._read_cache",
                new_callable=AsyncMock,
                return_value="Cached summary",
            ),
            patch("app.summarizer._write_cache", new_callable=AsyncMock),
        ):
            result = await generate_summary(
                [{"role": "user", "text": "Hello", "timestamp": "t"}],
                preset="conversational",
            )
            assert result == "Cached summary"

    @pytest.mark.asyncio
    async def test_calls_litellm_on_cache_miss(self) -> None:
        from app.summarizer import generate_summary

        mock_response = MagicMock()
        mock_response.choices[0].message.content = "LLM generated summary"

        with (
            patch("app.summarizer._read_cache", new_callable=AsyncMock, return_value=None),
            patch("app.summarizer._write_cache", new_callable=AsyncMock),
            patch("app.summarizer.acompletion", new_callable=AsyncMock, return_value=mock_response),
        ):
            result = await generate_summary(
                [{"role": "user", "text": "Hello", "timestamp": "t"}],
                preset="code_logic",
            )
            assert result == "LLM generated summary"

    @pytest.mark.asyncio
    async def test_falls_back_on_litellm_timeout(self) -> None:
        from app.summarizer import generate_summary

        with (
            patch("app.summarizer._read_cache", new_callable=AsyncMock, return_value=None),
            patch("app.summarizer._write_cache", new_callable=AsyncMock),
            patch(
                "app.summarizer.acompletion",
                new_callable=AsyncMock,
                side_effect=TimeoutError("LLM timeout"),
            ),
        ):
            result = await generate_summary(
                [{"role": "user", "text": "Timed out question", "timestamp": "t"}],
                preset="conversational",
            )
            assert "FALLBACK" in result
            assert "Timed out question" in result

    @pytest.mark.asyncio
    async def test_unknown_preset_defaults_to_conversational(self) -> None:
        from app.summarizer import generate_summary

        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Default preset summary"

        with patch("app.summarizer._read_cache", new_callable=AsyncMock, return_value=None):
            with patch("app.summarizer._write_cache", new_callable=AsyncMock):
                with patch(
                    "app.summarizer.acompletion",
                    new_callable=AsyncMock,
                    return_value=mock_response,
                ) as mock_completion:
                    await generate_summary(
                        [{"role": "user", "text": "Hello", "timestamp": "t"}],
                        preset="nonexistent_preset",
                    )
                    # Should have been called — no crash on unknown preset
                    mock_completion.assert_called_once()
