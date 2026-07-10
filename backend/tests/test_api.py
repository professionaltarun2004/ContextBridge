"""
ContextOS API Integration Tests — Full 6-endpoint suite in MOCK_MODE.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["mock_mode"] is True


@pytest.mark.asyncio
async def test_import_conversation(client: AsyncClient) -> None:
    payload = {
        "platform": "claude",
        "url": "https://claude.ai/chat/test-123",
        "messages": [
            {"id": "msg_1", "role": "user", "text": "Let's use FastAPI and Neo4j.", "timestamp": "2024-01-01T00:00:00Z"},
            {"id": "msg_2", "role": "assistant", "text": "Great choices! FastAPI is async and Neo4j excels at relationships.", "timestamp": "2024-01-01T00:01:00Z"},
        ],
    }
    resp = await client.post("/api/v1/import", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "conversation_id" in data
    assert data["nodes_extracted"] > 0


@pytest.mark.asyncio
async def test_get_graph_mock(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/graph")
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) > 0
    # Verify node structure
    node = data["nodes"][0]
    assert "id" in node
    assert "label" in node
    assert "properties" in node


@pytest.mark.asyncio
async def test_compile_backend_pack(client: AsyncClient) -> None:
    payload = {
        "conversation_id": "conv_mock_001",
        "role_pack": "backend",
        "selections": {
            "architecture": True,
            "apis": True,
            "database": True,
            "constraints": True,
        },
    }
    resp = await client.post("/api/v1/compile", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "pack_id" in data
    assert data["role_pack"] == "backend"
    assert len(data["files"]) > 0


@pytest.mark.asyncio
async def test_list_packs(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/packs")
    assert resp.status_code == 200
    data = resp.json()
    assert "packs" in data


@pytest.mark.asyncio
async def test_export_pack(client: AsyncClient) -> None:
    payload = {"pack_id": "pack_mock_001", "format": "zip"}
    resp = await client.post("/api/v1/export", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "download_url" in data
    assert "pack_mock_001" in data["download_url"]


@pytest.mark.asyncio
async def test_ask_question(client: AsyncClient) -> None:
    payload = {"question": "Why did we choose FastAPI?"}
    resp = await client.post("/api/v1/ask", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert "confidence_average" in data
    assert "citations" in data
    assert data["confidence_average"] > 0


@pytest.mark.asyncio
async def test_compile_frontend_pack(client: AsyncClient) -> None:
    payload = {
        "conversation_id": "conv_mock_001",
        "role_pack": "frontend",
        "selections": {"architecture": True, "coding_style": True, "constraints": True},
    }
    resp = await client.post("/api/v1/compile", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["role_pack"] == "frontend"
