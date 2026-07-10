"""
ContextOS Backend — API Schemas (Pydantic)
Strict typed contracts for all 6 REST endpoints.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# POST /api/v1/import
# ---------------------------------------------------------------------------

class RawMessage(BaseModel):
    id: str
    role: str  # "user" | "assistant"
    text: str
    timestamp: str


class ImportRequest(BaseModel):
    platform: str = Field(..., examples=["claude", "chatgpt", "gemini"])
    url: str
    messages: list[RawMessage]


class ImportResponse(BaseModel):
    status: str
    conversation_id: str
    nodes_extracted: int
    relationships_created: int
    execution_time_ms: int


# ---------------------------------------------------------------------------
# POST /api/v1/compile
# ---------------------------------------------------------------------------

class PackSelections(BaseModel):
    architecture: bool = True
    apis: bool = True
    database: bool = False
    constraints: bool = True
    tasks: bool = False
    coding_style: bool = False
    current_progress: bool = False


class CompileRequest(BaseModel):
    conversation_id: str
    role_pack: str = Field(..., examples=["backend", "frontend", "devops", "bugfix"])
    selections: PackSelections = Field(default_factory=PackSelections)


class CompileResponse(BaseModel):
    pack_id: str
    role_pack: str
    files: dict[str, str]


# ---------------------------------------------------------------------------
# GET /api/v1/graph
# ---------------------------------------------------------------------------

class GraphNode(BaseModel):
    id: str
    label: str
    properties: dict[str, Any]


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


# ---------------------------------------------------------------------------
# GET /api/v1/packs
# ---------------------------------------------------------------------------

class PackSummary(BaseModel):
    pack_id: str
    role_pack: str
    created_at: str


class PacksResponse(BaseModel):
    packs: list[PackSummary]


# ---------------------------------------------------------------------------
# POST /api/v1/export
# ---------------------------------------------------------------------------

class ExportRequest(BaseModel):
    pack_id: str
    format: str = Field(default="zip", examples=["zip", "markdown"])


class ExportResponse(BaseModel):
    download_url: str


# ---------------------------------------------------------------------------
# POST /api/v1/ask
# ---------------------------------------------------------------------------

class AskRequest(BaseModel):
    question: str


class Citation(BaseModel):
    node_id: str
    node_label: str
    source_message: str
    source_ai: str
    conversation_id: str


class AskResponse(BaseModel):
    answer: str
    confidence_average: float
    citations: list[Citation]
