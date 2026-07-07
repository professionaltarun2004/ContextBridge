"""
24-Hour Transient Data Purge Daemon.
FR-005 / Data Requirements: Raw conversation histories are purged exactly 24 hours after sync.
Uses APScheduler to run an in-process background job without requiring Celery.
VectorChunks are preserved after purge (cascade delete does NOT apply to raw_chat_history).

Upgrade path: Replace APScheduler with Celery Beat + Redis broker for distributed deployments.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import update

from app.database import AsyncSessionLocal
from app.models import Conversation

logger = logging.getLogger(__name__)

_scheduler = AsyncIOScheduler()


async def purge_expired_raw_histories() -> None:
    """
    Nullifies raw_chat_history for Conversations older than 24 hours.
    VectorChunks remain intact — only the raw JSONB column is cleared.
    This satisfies the transient data retention policy while preserving
    semantic memory.
    """
    cutoff = datetime.now(UTC) - timedelta(hours=24)

    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(
                update(Conversation)
                .where(
                    Conversation.created_at < cutoff,
                    Conversation.raw_chat_history.is_not(None),
                )
                .values(raw_chat_history=None)
                .returning(Conversation.id)
            )
            purged_ids = result.fetchall()
            count = len(purged_ids)

    if count > 0:
        logger.info(
            "Purge daemon: Nullified raw_chat_history for %d conversation(s) "
            "older than 24 hours.",
            count,
        )
    else:
        logger.debug("Purge daemon: No expired conversations found.")


def start_purge_scheduler() -> None:
    """
    Registers the purge job and starts the APScheduler.
    Called once at application startup.
    """
    _scheduler.add_job(
        purge_expired_raw_histories,
        trigger="interval",
        hours=1,  # Run every hour to catch any missed purges
        id="purge_raw_histories",
        name="24h Raw History Purge",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Purge daemon scheduler started (hourly interval).")


def stop_purge_scheduler() -> None:
    """
    Gracefully shuts down the scheduler on application teardown.
    """
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Purge daemon scheduler stopped.")
