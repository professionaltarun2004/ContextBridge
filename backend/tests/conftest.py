"""
ContextOS Backend Tests — MOCK_MODE suite.
All tests run with MOCK_MODE=True, requiring zero real services.
"""
from __future__ import annotations

import os

os.environ.setdefault("NEO4J_URI", "neo4j+s://mock.databases.neo4j.io")
os.environ.setdefault("NEO4J_USERNAME", "neo4j")
os.environ.setdefault("NEO4J_PASSWORD", "mock_password")
os.environ.setdefault("OPENAI_API_KEY", "sk-dummy")
os.environ.setdefault("GEMINI_API_KEY", "dummy")
os.environ.setdefault("MOCK_MODE", "True")

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():  # type: ignore[return]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
