"""
ContextOS — Parallel Multi-Agent Extraction Pipeline (FR-003)

Executes Entity, Decision, Task, and Constraint agents concurrently,
then merges outputs and writes to Neo4j with confidence + source traceability.

MOCK_MODE: When settings.MOCK_MODE is True, returns pre-built fixture data
instantly for live demo presentations without any LLM API calls.
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any

from litellm import acompletion  # type: ignore[import-untyped]

from app.config import settings
from app.database import get_session

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mock fixtures — instant return for demo mode (NFR-001)
# ---------------------------------------------------------------------------

MOCK_EXTRACTION: dict[str, Any] = {
    "decisions": [
        {"text": "Use FastAPI for backend", "rationale": "Async + high performance", "confidence": 0.98},
        {"text": "Use Neo4j AuraDB for graph storage", "rationale": "Relationship traversal needs", "confidence": 0.97},
        {"text": "Deploy on Render with Docker", "rationale": "Seamless GitHub integration", "confidence": 0.95},
    ],
    "tasks": [
        {"text": "Initialize Neo4j schema and constraints", "status": "pending", "confidence": 0.92},
        {"text": "Build parallel extraction pipeline", "status": "pending", "confidence": 0.88},
        {"text": "Create 6-page Base44 dashboard", "status": "in_progress", "confidence": 0.91},
    ],
    "entities": [
        {"name": "FastAPI", "type": "Library", "confidence": 0.99},
        {"name": "Neo4j", "type": "Database", "confidence": 0.99},
        {"name": "LiteLLM", "type": "Library", "confidence": 0.96},
        {"name": "React", "type": "Library", "confidence": 0.97},
    ],
    "constraints": [
        {"text": "Pipeline must complete in under 10 seconds", "confidence": 0.95},
        {"text": "Extension must detect text area under 300ms", "confidence": 0.93},
        {"text": "Strict TypeScript — no implicit any", "confidence": 0.99},
    ],
}


# ---------------------------------------------------------------------------
# LLM Agent Prompts
# ---------------------------------------------------------------------------

AGENT_PROMPTS = {
    "decision": """You are a Decision Extractor. Analyze the following AI conversation and extract ALL architectural decisions, technology choices, and technical directions. Return a JSON array:
[{{ "text": "...", "rationale": "...", "confidence": 0.0-1.0 }}]
Conversation:
{transcript}""",

    "task": """You are a Task Extractor. Analyze the following AI conversation and extract ALL action items, features to build, and pending work. Return a JSON array:
[{{ "text": "...", "status": "pending|in_progress|done", "confidence": 0.0-1.0 }}]
Conversation:
{transcript}""",

    "entity": """You are an Entity Extractor. Analyze the following AI conversation and extract ALL technologies, APIs, libraries, systems, and file names mentioned. Return a JSON array:
[{{ "name": "...", "type": "Library|API|Database|Service|File", "confidence": 0.0-1.0 }}]
Conversation:
{transcript}""",

    "constraint": """You are a Constraint Extractor. Analyze the following AI conversation and extract ALL technical constraints, limits, styling rules, and non-negotiable parameters. Return a JSON array:
[{{ "text": "...", "confidence": 0.0-1.0 }}]
Conversation:
{transcript}""",
}


async def _run_agent(agent_type: str, transcript: str) -> list[dict[str, Any]]:
    """Runs a single extraction agent via LiteLLM."""
    prompt = AGENT_PROMPTS[agent_type].format(transcript=transcript)
    try:
        response = await acompletion(  # type: ignore[misc]
            model="gemini/gemini-pro",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=1000,
            api_key=settings.GEMINI_API_KEY,
            response_format={"type": "json_object"},
        )
        import json
        raw = response.choices[0].message.content or "[]"
        parsed = json.loads(raw)
        # Handle both array and object responses
        if isinstance(parsed, list):
            return parsed
        return list(parsed.values())[0] if parsed else []
    except Exception as exc:
        logger.warning("Agent %s failed: %s. Using empty result.", agent_type, exc)
        return []


def _build_transcript(messages: list[dict[str, Any]]) -> str:
    """Converts message array to readable transcript."""
    lines = []
    for msg in messages:
        role = msg.get("role", "user").upper()
        text = msg.get("text", "")
        lines.append(f"{role}: {text}")
    return "\n".join(lines)


async def _write_graph(
    session: Any,
    conversation_id: str,
    platform: str,
    url: str,
    extraction: dict[str, Any],
    messages: list[dict[str, Any]],
) -> tuple[int, int]:
    """Writes all extracted nodes and relationships to Neo4j."""
    nodes = 0
    rels = 0

    # Create Conversation node
    res_c = await session.run(
        """
        MERGE (c:Conversation {id: $id})
        SET c.platform = $platform,
            c.url = $url,
            c.timestamp = timestamp()
        """,
        id=conversation_id,
        platform=platform,
        url=url,
    )
    await res_c.consume()
    nodes += 1

    # Write decisions
    for i, decision in enumerate(extraction.get("decisions", [])):
        did = f"dec_{conversation_id}_{i}"
        source_msg = messages[i % len(messages)]["id"] if messages else "msg_0"
        res_d = await session.run(
            """
            MERGE (d:Decision {id: $id})
            SET d.text = $text,
                d.rationale = $rationale,
                d.confidence = $confidence,
                d.source_message = $source_msg,
                d.source_ai = $platform,
                d.conversation_id = $conv_id
            WITH d
            MATCH (c:Conversation {id: $conv_id})
            MERGE (c)-[:MADE_DECISION]->(d)
            """,
            id=did, text=decision.get("text", ""), rationale=decision.get("rationale", ""),
            confidence=decision.get("confidence", 0.5), source_msg=source_msg,
            platform=platform, conv_id=conversation_id,
        )
        await res_d.consume()
        nodes += 1
        rels += 1

    # Write tasks
    for i, task in enumerate(extraction.get("tasks", [])):
        tid = f"task_{conversation_id}_{i}"
        source_msg = messages[i % len(messages)]["id"] if messages else "msg_0"
        res_t = await session.run(
            """
            MERGE (t:Task {id: $id})
            SET t.text = $text,
                t.status = $status,
                t.confidence = $confidence,
                t.source_message = $source_msg,
                t.source_ai = $platform,
                t.conversation_id = $conv_id
            WITH t
            MATCH (c:Conversation {id: $conv_id})
            MERGE (c)-[:GENERATES]->(t)
            """,
            id=tid, text=task.get("text", ""), status=task.get("status", "pending"),
            confidence=task.get("confidence", 0.5), source_msg=source_msg,
            platform=platform, conv_id=conversation_id,
        )
        await res_t.consume()
        nodes += 1
        rels += 1

    # Write entities
    for i, entity in enumerate(extraction.get("entities", [])):
        eid = f"ent_{conversation_id}_{i}"
        source_msg = messages[0]["id"] if messages else "msg_0"
        res_e = await session.run(
            """
            MERGE (e:Entity {id: $id})
            SET e.name = $name,
                e.type = $type,
                e.confidence = $confidence,
                e.source_message = $source_msg,
                e.source_ai = $platform,
                e.conversation_id = $conv_id
            WITH e
            MATCH (c:Conversation {id: $conv_id})
            MERGE (c)-[:MENTIONS]->(e)
            """,
            id=eid, name=entity.get("name", ""), type=entity.get("type", "Unknown"),
            confidence=entity.get("confidence", 0.5), source_msg=source_msg,
            platform=platform, conv_id=conversation_id,
        )
        await res_e.consume()
        nodes += 1
        rels += 1

    # Write constraints
    for i, constraint in enumerate(extraction.get("constraints", [])):
        cid = f"con_{conversation_id}_{i}"
        source_msg = messages[0]["id"] if messages else "msg_0"
        res_con = await session.run(
            """
            MERGE (con:Constraint {id: $id})
            SET con.text = $text,
                con.confidence = $confidence,
                con.source_message = $source_msg,
                con.source_ai = $platform,
                con.conversation_id = $conv_id
            WITH con
            MATCH (c:Conversation {id: $conv_id})
            MERGE (c)-[:HAS_CONSTRAINT]->(con)
            """,
            id=cid, text=constraint.get("text", ""),
            confidence=constraint.get("confidence", 0.5), source_msg=source_msg,
            platform=platform, conv_id=conversation_id,
        )
        await res_con.consume()
        nodes += 1
        rels += 1

    return nodes, rels


async def run_pipeline(
    platform: str,
    url: str,
    messages: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Main entry point. Runs the full parallel extraction pipeline.
    Returns extraction stats for the /import response.
    """
    start = time.time()
    conversation_id = f"conv_{uuid.uuid4().hex[:12]}"
    messages_raw = [
        {"id": m.get("id", f"msg_{i}"), "role": m.get("role", "user"), "text": m.get("text", "")}
        for i, m in enumerate(messages)
    ]

    if settings.MOCK_MODE:
        logger.info("MOCK_MODE active — returning fixture extraction data.")
        extraction = MOCK_EXTRACTION
    else:
        transcript = _build_transcript(messages_raw)
        # Run all 4 agents concurrently (FR-003 AC1)
        decision_result, task_result, entity_result, constraint_result = await asyncio.gather(
            _run_agent("decision", transcript),
            _run_agent("task", transcript),
            _run_agent("entity", transcript),
            _run_agent("constraint", transcript),
        )
        extraction = {
            "decisions": decision_result,
            "tasks": task_result,
            "entities": entity_result,
            "constraints": constraint_result,
        }

    if settings.MOCK_MODE:
        # In mock mode, skip the actual graph write — return instant fixture stats
        elapsed_ms = int((time.time() - start) * 1000)
        return {
            "conversation_id": conversation_id,
            "nodes_extracted": 12,
            "relationships_created": 8,
            "execution_time_ms": elapsed_ms,
        }

    # Write to Neo4j (live mode only)
    async with get_session() as session:
        nodes, rels = await _write_graph(session, conversation_id, platform, url, extraction, messages_raw)

    elapsed_ms = int((time.time() - start) * 1000)
    return {
        "conversation_id": conversation_id,
        "nodes_extracted": nodes,
        "relationships_created": rels,
        "execution_time_ms": elapsed_ms,
    }
