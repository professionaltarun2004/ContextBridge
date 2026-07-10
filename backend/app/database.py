"""
Neo4j AuraDB Connection Driver.
Manages the async bolt connection pool for the ContextOS graph engine.
"""
from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from neo4j import AsyncDriver, AsyncGraphDatabase

from app.config import settings

logger = logging.getLogger(__name__)

_driver: AsyncDriver | None = None


def get_driver() -> AsyncDriver:
    """Returns the shared AsyncDriver instance."""
    if _driver is None:
        raise RuntimeError("Neo4j driver not initialized. Call init_driver() first.")
    return _driver


async def init_driver() -> None:
    """Creates the shared Neo4j AsyncDriver at application startup."""
    global _driver
    _driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD),
    )
    # Verify connectivity
    await _driver.verify_connectivity()
    logger.info("Neo4j AuraDB connection established.")


async def close_driver() -> None:
    """Closes the shared driver at application shutdown."""
    global _driver
    if _driver is not None:
        await _driver.close()
        _driver = None
        logger.info("Neo4j driver closed.")


@asynccontextmanager
async def get_session() -> AsyncGenerator:
    """Async context manager yielding a Neo4j session."""
    driver = get_driver()
    async with driver.session() as session:
        yield session
