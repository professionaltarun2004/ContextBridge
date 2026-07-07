"""
Shared pytest fixtures for ContextBridge backend tests.
Uses in-memory SQLite for DB tests and httpx AsyncClient for API tests.
"""

from __future__ import annotations

import os
from pathlib import Path


def _load_test_env() -> None:
    """
    Loads test environment variables from .env.test BEFORE any app module is
    imported. This prevents Pydantic Settings validation from failing due to
    missing production credentials during local/CI testing.

    Defined as a function so that all subsequent imports are NOT flagged as
    E402 (module-level import not at top of file) by ruff.
    """
    env_file = Path(__file__).parent / ".env.test"
    if env_file.exists():
        for raw_line in env_file.read_text().splitlines():
            raw_line = raw_line.strip()
            if raw_line and not raw_line.startswith("#") and "=" in raw_line:
                key, _, value = raw_line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


_load_test_env()

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from collections.abc import AsyncGenerator  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.database import get_db  # noqa: E402
from app.main import app  # noqa: E402

# ---------------------------------------------------------------------------
# Test Database — SQLite in-memory (without pgvector/JSONB for compatibility)
# We use the app's SQLAlchemy Base but only create compatible tables.
# API tests that need the full DB mock at the router level.
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Provides an async SQLite test session.
    Creates tables using raw SQL to avoid pgvector/JSONB incompatibilities.
    """
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        # Create tables compatible with SQLite (no pgvector, plain JSON)
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id VARCHAR(255) PRIMARY KEY,
                email VARCHAR(255) NOT NULL,
                stripe_customer_id VARCHAR(255) UNIQUE,
                is_subscribed BOOLEAN NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                source_platform VARCHAR(50) NOT NULL,
                raw_chat_history TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS vector_chunks (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                embedding TEXT NOT NULL,
                summary_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with session_factory() as session:
        yield session

    await engine.dispose()


# ---------------------------------------------------------------------------
# API Client Fixture
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="function")
async def client(test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient with DB dependency overridden to use the test database."""

    async def override_get_db() -> AsyncSession:  # type: ignore[return]
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Mock Auth Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_paid_auth() -> dict:  # type: ignore[type-arg]
    return {"sub": "auth0|test_paid_user", "email": "paid@example.com"}


@pytest.fixture
def mock_free_auth() -> dict:  # type: ignore[type-arg]
    return {"sub": "auth0|test_free_user", "email": "free@example.com"}
