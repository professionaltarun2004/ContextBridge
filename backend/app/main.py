"""
ContextOS FastAPI Backend — All 6 REST endpoints (FR-010).
"""
from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.ask_engine import traverse_and_answer
from app.config import settings
from app.database import close_driver, get_session, init_driver
from app.pack_generator import compile_pack
from app.pipeline import run_pipeline
from app.schemas import (
    AskRequest,
    AskResponse,
    Citation,
    CompileRequest,
    CompileResponse,
    ExportRequest,
    ExportResponse,
    GraphEdge,
    GraphNode,
    GraphResponse,
    ImportRequest,
    ImportResponse,
    PacksResponse,
    PackSummary,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manages Neo4j driver lifecycle."""
    if not settings.MOCK_MODE:
        await init_driver()
    else:
        logger.info("MOCK_MODE=True — skipping Neo4j connection.")
    yield
    if not settings.MOCK_MODE:
        await close_driver()


app = FastAPI(
    title="ContextOS API",
    description="The Operating System for AI Work — 6-endpoint context intelligence gateway.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/", tags=["Health"])
async def root() -> dict[str, str]:
    return {"message": "ContextOS API is running. Go to /openapi.json for docs."}


@app.get("/health", tags=["Health"])
async def health() -> dict:  # type: ignore[type-arg]
    return {"status": "healthy", "mock_mode": settings.MOCK_MODE, "version": "1.0.0"}


# ---------------------------------------------------------------------------
# POST /api/v1/import — Trigger parallel multi-agent pipeline
# ---------------------------------------------------------------------------

@app.post("/api/v1/import", response_model=ImportResponse, tags=["Pipeline"])
async def import_conversation(payload: ImportRequest) -> ImportResponse:
    """
    Receives raw conversation from the Chrome Extension and executes
    the parallel multi-agent extraction pipeline (FR-003).
    """
    messages = [m.model_dump() for m in payload.messages]
    result = await run_pipeline(
        platform=payload.platform,
        url=payload.url,
        messages=messages,
    )
    return ImportResponse(status="success", **result)


# ---------------------------------------------------------------------------
# POST /api/v1/compile — Compile Smart Context Pack
# ---------------------------------------------------------------------------

@app.post("/api/v1/compile", response_model=CompileResponse, tags=["Packs"])
async def compile_context_pack(payload: CompileRequest) -> CompileResponse:
    """
    Compiles a role-specific Smart Context Pack from Project Memory (FR-007).
    """
    result = await compile_pack(
        conversation_id=payload.conversation_id,
        role_pack=payload.role_pack,
        selections=payload.selections.model_dump(),
    )
    return CompileResponse(**result)


# ---------------------------------------------------------------------------
# GET /api/v1/graph — Fetch Knowledge Graph for visualization
# ---------------------------------------------------------------------------

@app.get("/api/v1/graph", response_model=GraphResponse, tags=["Graph"])
async def get_graph(conversation_id: str | None = None) -> GraphResponse:
    """
    Returns Neo4j graph nodes and edges for the dashboard visualizer (FR-005).
    """
    if settings.MOCK_MODE:
        # Return a rich mock graph for demo visualization
        nodes = [
            GraphNode(id="c0", label="Conversation", properties={"platform": "Claude", "title": "ContextOS Architecture"}),
            GraphNode(id="d0", label="Decision", properties={"text": "Use FastAPI", "confidence": 0.98, "source_ai": "Claude", "source_message": "msg_42"}),
            GraphNode(id="d1", label="Decision", properties={"text": "Use Neo4j AuraDB", "confidence": 0.97, "source_ai": "Claude", "source_message": "msg_55"}),
            GraphNode(id="d2", label="Decision", properties={"text": "Deploy on Render", "confidence": 0.95, "source_ai": "Claude", "source_message": "msg_60"}),
            GraphNode(id="t0", label="Task", properties={"text": "Initialize Neo4j schema", "status": "pending", "confidence": 0.92}),
            GraphNode(id="t1", label="Task", properties={"text": "Build parallel pipeline", "status": "in_progress", "confidence": 0.88}),
            GraphNode(id="e0", label="Entity", properties={"name": "FastAPI", "type": "Library", "confidence": 0.99}),
            GraphNode(id="e1", label="Entity", properties={"name": "Neo4j", "type": "Database", "confidence": 0.99}),
            GraphNode(id="e2", label="Entity", properties={"name": "LiteLLM", "type": "Library", "confidence": 0.96}),
            GraphNode(id="con0", label="Constraint", properties={"text": "Pipeline < 10 seconds", "confidence": 0.95}),
        ]
        edges = [
            GraphEdge(id="r0", source="c0", target="d0", type="MADE_DECISION"),
            GraphEdge(id="r1", source="c0", target="d1", type="MADE_DECISION"),
            GraphEdge(id="r2", source="c0", target="d2", type="MADE_DECISION"),
            GraphEdge(id="r3", source="c0", target="t0", type="GENERATES"),
            GraphEdge(id="r4", source="c0", target="t1", type="GENERATES"),
            GraphEdge(id="r5", source="c0", target="e0", type="MENTIONS"),
            GraphEdge(id="r6", source="c0", target="e1", type="MENTIONS"),
            GraphEdge(id="r7", source="c0", target="e2", type="MENTIONS"),
            GraphEdge(id="r8", source="d0", target="e0", type="USES"),
            GraphEdge(id="r9", source="d1", target="e1", type="USES"),
            GraphEdge(id="r10", source="c0", target="con0", type="HAS_CONSTRAINT"),
        ]
        return GraphResponse(nodes=nodes, edges=edges)

    nodes = []
    edges = []
    async with get_session() as session:
        cypher = (
            "MATCH (n)-[r]->(m) WHERE $conv_id IS NULL OR n.conversation_id = $conv_id "
            "RETURN n, labels(n) AS nl, r, type(r) AS rt, m, labels(m) AS ml LIMIT 200"
        )
        result = await session.run(cypher, conv_id=conversation_id)
        seen_nodes: set[str] = set()
        async for record in result:
            for node, label_list in [(record["n"], record["nl"]), (record["m"], record["ml"])]:
                nid = node.element_id
                if nid not in seen_nodes:
                    seen_nodes.add(nid)
                    nodes.append(GraphNode(
                        id=nid,
                        label=label_list[0] if label_list else "Unknown",
                        properties=dict(node),
                    ))
            edges.append(GraphEdge(
                id=record["r"].element_id,
                source=record["n"].element_id,
                target=record["m"].element_id,
                type=record["rt"],
            ))

    return GraphResponse(nodes=nodes, edges=edges)


# ---------------------------------------------------------------------------
# GET /api/v1/packs — List available Smart Packs
# ---------------------------------------------------------------------------

@app.get("/api/v1/packs", response_model=PacksResponse, tags=["Packs"])
async def list_packs() -> PacksResponse:
    """Returns all generated Smart Context Packs (FR-007)."""
    if settings.MOCK_MODE:
        return PacksResponse(packs=[
            PackSummary(pack_id="pack_mock_001", role_pack="backend", created_at="2024-07-10T10:00:00Z"),
        ])

    packs = []
    async with get_session() as session:
        result = await session.run("MATCH (p:ContextPack) RETURN p ORDER BY p.created_at DESC LIMIT 50")
        async for record in result:
            p = dict(record["p"])
            packs.append(PackSummary(
                pack_id=p.get("id", ""),
                role_pack=p.get("role_pack", ""),
                created_at=str(p.get("created_at", "")),
            ))
    return PacksResponse(packs=packs)


# ---------------------------------------------------------------------------
# POST /api/v1/export — Export pack as download
# ---------------------------------------------------------------------------

@app.post("/api/v1/export", response_model=ExportResponse, tags=["Export"])
async def export_pack(payload: ExportRequest) -> ExportResponse:
    """Bundles a Smart Pack and returns a download URL (FR-007 AC2)."""
    # V1: Return a direct markdown bundle URL. Full zip generation is Phase 2.
    return ExportResponse(
        download_url=f"https://api.contextos.dev/exports/{payload.pack_id}.{payload.format}"
    )


# ---------------------------------------------------------------------------
# POST /api/v1/ask — Graph traversal Q&A
# ---------------------------------------------------------------------------

@app.post("/api/v1/ask", response_model=AskResponse, tags=["Ask"])
async def ask(payload: AskRequest) -> AskResponse:
    """
    Traverses the Neo4j Knowledge Graph to answer natural language
    developer questions with source citations (FR-009).
    """
    result = await traverse_and_answer(payload.question)
    citations = [Citation(**c) for c in result.get("citations", [])]
    return AskResponse(
        answer=result["answer"],
        confidence_average=result["confidence_average"],
        citations=citations,
    )
