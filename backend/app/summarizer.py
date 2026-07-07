"""
LiteLLM Summarization Engine with Redis Caching.
FR-003: Generates instruction-optimized summaries using configurable presets.
NFR-002: < 1.5 second total latency; < 200ms TTFT via streaming.
T12: Redis cache keyed as summary:cache:{SHA256}:{preset} with 2h TTL.
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import AsyncIterator

import redis.asyncio as aioredis
from typing import Any, Callable, cast
from litellm import acompletion as _acompletion  # type: ignore[import-untyped]

acompletion = cast(Callable[..., Any], _acompletion)

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Summarization Presets — FR-003, AC2
# ---------------------------------------------------------------------------

PRESETS: dict[str, str] = {
    "code_logic": (
        "You are a technical context bridge. Given the following AI conversation, "
        "produce an ultra-dense system prompt (max 300 tokens) that captures all: "
        "programming languages, frameworks, architectural decisions, specific functions, "
        "variables, bugs discussed, and action items. Prioritize technical precision. "
        "Output ONLY the system prompt text, nothing else."
    ),
    "conversational": (
        "You are a conversation summarizer. Given the following AI conversation, "
        "produce a concise context block (max 300 tokens) capturing the main topics, "
        "user goals, decisions made, and next steps discussed. Write in a neutral, "
        "informative tone. Output ONLY the summary text, nothing else."
    ),
    "ultra_dense": (
        "You are an information compression engine. Given the following AI conversation, "
        "produce the most token-efficient possible context block (max 150 tokens) that "
        "retains all critical information needed to continue the conversation without loss. "
        "Use abbreviations where safe. Output ONLY the compressed context, nothing else."
    ),
}

DEFAULT_PRESET = "conversational"

# ---------------------------------------------------------------------------
# Redis Cache Client — T12
# ---------------------------------------------------------------------------

_redis_client: aioredis.Redis | None = None  # type: ignore[type-arg]


async def get_redis() -> aioredis.Redis | None:  # type: ignore[type-arg]
    """Returns a Redis client, or None if Redis is unavailable."""
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            await _redis_client.ping()
        except Exception as exc:
            logger.warning("Redis unavailable: %s — cache bypassed", exc)
            _redis_client = None
    return _redis_client


def _build_cache_key(messages_json: str, preset: str) -> str:
    """
    Constructs the Redis cache key: summary:cache:{SHA256_OF_MESSAGES}:{preset}
    Matches the key schema from the Solution architecture.
    """
    sha256 = hashlib.sha256(messages_json.encode()).hexdigest()
    return f"summary:cache:{sha256}:{preset}"


CACHE_TTL_SECONDS = 7200  # 2 hours — volatile-lru eviction policy


async def _read_cache(key: str) -> str | None:
    redis = await get_redis()
    if redis is None:
        return None
    try:
        res = await redis.get(key)
        return str(res) if res is not None else None
    except Exception as exc:
        logger.warning("Redis read failed: %s", exc)
        return None


async def _write_cache(key: str, value: str) -> None:
    redis = await get_redis()
    if redis is None:
        return
    try:
        await redis.setex(key, CACHE_TTL_SECONDS, value)
    except Exception as exc:
        logger.warning("Redis write failed: %s", exc)


# ---------------------------------------------------------------------------
# Fallback Summarizer — FR-003, AC3 / Solution: LiteLLM Timeout
# ---------------------------------------------------------------------------

def _deterministic_fallback(messages: list[dict]) -> str:  # type: ignore[type-arg]
    """
    Deterministic fallback: combines last 3 dialogue turns into a raw summary.
    Used when LiteLLM times out or returns an error.
    """
    last_turns = messages[-6:]  # up to 3 full exchanges
    lines = [
        f"[{m['role'].upper()}]: {str(m['text'])[:300]}"
        for m in last_turns
    ]
    return "[FALLBACK CONTEXT — LLM UNAVAILABLE]\n\n" + "\n\n".join(lines)


# ---------------------------------------------------------------------------
# Embedding Generation
# ---------------------------------------------------------------------------

async def generate_embeddings(text: str) -> list[float]:
    """
    Generates 1536-dimensional embeddings using OpenAI text-embedding-3-small.
    """
    from litellm import aembedding  # type: ignore[import-untyped]

    response = await aembedding(
        model="text-embedding-3-small",
        input=[text],
        api_key=settings.OPENAI_API_KEY,
    )
    return response.data[0]["embedding"]  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Main Summarizer
# ---------------------------------------------------------------------------

async def generate_summary(
    messages: list[dict],  # type: ignore[type-arg]
    preset: str = DEFAULT_PRESET,
) -> str:
    """
    Generates an instruction-optimized summary of a conversation.

    1. Checks Redis cache — returns immediately on hit.
    2. Calls LiteLLM with a 1.4s timeout (leaving 100ms headroom for NFR-002).
    3. Falls back to deterministic summarization on timeout or API failure.
    4. Writes result to Redis cache.

    Args:
        messages: List of {role, text, timestamp} dicts.
        preset: Summarization style key ("code_logic" | "conversational" | "ultra_dense").
    Returns:
        Instruction-optimized context string.
    """
    if preset not in PRESETS:
        preset = DEFAULT_PRESET

    messages_json = json.dumps(messages, sort_keys=True)
    cache_key = _build_cache_key(messages_json, preset)

    # 1. Cache hit
    cached = await _read_cache(cache_key)
    if cached is not None:
        logger.debug("Cache hit for key prefix: %s", cache_key[:32])
        return cached

    # 2. Build the conversation transcript for the prompt
    transcript = "\n".join(
        f"{m['role'].upper()}: {m['text']}" for m in messages
    )
    system_prompt = PRESETS[preset]
    user_message = f"CONVERSATION:\n{transcript}\n\nGenerate the context block now:"

    # 3. LiteLLM call with timeout
    summary: str
    try:
        response = await acompletion(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=350,
            temperature=0.3,
            timeout=1.4,
            api_key=settings.OPENAI_API_KEY,
            fallbacks=[
                {
                    "model": "claude-3-haiku-20240307",
                    "api_key": settings.ANTHROPIC_API_KEY,
                }
            ],
        )
        summary = response.choices[0].message.content or _deterministic_fallback(messages)
    except Exception as exc:
        logger.warning("LiteLLM summarization failed (using fallback): %s", exc)
        summary = _deterministic_fallback(messages)

    # 4. Cache the result
    await _write_cache(cache_key, summary)

    return summary


async def stream_summary(
    messages: list[dict],  # type: ignore[type-arg]
    preset: str = DEFAULT_PRESET,
) -> AsyncIterator[str]:
    """
    Streams a summary for TTFT < 200ms (NFR-002).
    Yields text chunks as they arrive from the model.
    Falls back to yielding the deterministic fallback as a single chunk.
    """
    if preset not in PRESETS:
        preset = DEFAULT_PRESET

    transcript = "\n".join(f"{m['role'].upper()}: {m['text']}" for m in messages)
    system_prompt = PRESETS[preset]
    user_message = f"CONVERSATION:\n{transcript}\n\nGenerate the context block now:"

    try:
        response = await acompletion(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=350,
            temperature=0.3,
            timeout=1.4,
            stream=True,
            api_key=settings.OPENAI_API_KEY,
        )
        async for chunk in response:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
    except Exception as exc:
        logger.warning("LiteLLM stream failed (using fallback): %s", exc)
        yield _deterministic_fallback(messages)
