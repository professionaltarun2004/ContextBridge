"""
ContextBridge Kernel — Memory Object Architecture

This module defines the canonical Application Binary Interface (ABI) for the entire platform.
It acts as the OS Kernel: absolutely provider-agnostic, strictly typed, and fundamentally graph-based.

Phase 1: Defining the Canonical Schema.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    CONVERSATION = "conversation"
    DECISION = "decision"
    GOAL = "goal"
    BUG = "bug"
    ARCHITECTURE = "architecture"
    API = "api"
    TIMELINE_EVENT = "timeline_event"
    CONSTRAINT = "constraint"
    LEARNING = "learning"
    PREFERENCE = "preference"
    CHECKPOINT = "checkpoint"
    UNKNOWN = "unknown"


class RelationshipType(str, Enum):
    DEPENDS_ON = "depends_on"
    IMPLEMENTS = "implements"
    BLOCKS = "blocks"
    DECIDES = "decides"
    MENTIONS = "mentions"
    RELATES_TO = "relates_to"


class MemoryRelationship(BaseModel):
    target_id: str
    relation: RelationshipType
    metadata: dict[str, str] = Field(default_factory=dict)


class MemoryObject(BaseModel):
    """
    The canonical, universal unit of memory across the entire OS.
    Everything must compile down to this.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: MemoryType
    title: str
    content: str
    
    # Graph Links
    relationships: list[MemoryRelationship] = Field(default_factory=list)
    
    # Heuristics for the Planner/Scheduler
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    freshness: float = Field(default=1.0, ge=0.0, le=1.0)
    
    # Ownership & Provenance
    owner: str = Field(default="system")
    project: str | None = None
    source: str  # e.g., "genesis://PLAN.md", "github://issue/123", "chrome-extension://chatgpt"
    
    # Extension payload
    metadata: dict[str, Any] = Field(default_factory=dict)
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
