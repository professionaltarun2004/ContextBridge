"""
ContextOS — Smart Context Pack Generator (FR-007)
Compiles role-specific Context Packs from Neo4j Project Memory.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from app.config import settings
from app.database import get_session

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Role Pack Templates — defines which sections each pack includes
# ---------------------------------------------------------------------------

PACK_TEMPLATES: dict[str, list[str]] = {
    "backend":   ["architecture", "apis", "database", "constraints"],
    "frontend":  ["architecture", "coding_style", "constraints", "current_progress"],
    "devops":    ["constraints", "architecture", "database"],
    "bugfix":    ["current_progress", "tasks", "constraints"],
}


async def _fetch_project_memory(conversation_id: str) -> dict[str, Any]:
    """Queries Neo4j and assembles the canonical Project Memory."""
    memory: dict[str, Any] = {
        "decisions": [], "tasks": [], "entities": [], "constraints": [],
    }

    if settings.MOCK_MODE:
        from app.pipeline import MOCK_EXTRACTION
        return MOCK_EXTRACTION

    async with get_session() as session:
        # Fetch decisions
        result = await session.run(
            "MATCH (c:Conversation {id: $id})-[:MADE_DECISION]->(d:Decision) RETURN d",
            id=conversation_id,
        )
        memory["decisions"] = [record["d"] async for record in result]

        # Fetch tasks
        result = await session.run(
            "MATCH (c:Conversation {id: $id})-[:GENERATES]->(t:Task) RETURN t",
            id=conversation_id,
        )
        memory["tasks"] = [record["t"] async for record in result]

        # Fetch entities
        result = await session.run(
            "MATCH (c:Conversation {id: $id})-[:MENTIONS]->(e:Entity) RETURN e",
            id=conversation_id,
        )
        memory["entities"] = [record["e"] async for record in result]

        # Fetch constraints
        result = await session.run(
            "MATCH (c:Conversation {id: $id})-[:HAS_CONSTRAINT]->(con:Constraint) RETURN con",
            id=conversation_id,
        )
        memory["constraints"] = [record["con"] async for record in result]

    return memory


def _compile_section(section: str, memory: dict[str, Any]) -> str:
    """Renders a single markdown section from Project Memory data."""
    if section == "architecture":
        entities = memory.get("entities", [])
        lines = ["# System Architecture\n"]
        tech_stack = [e.get("name", str(e)) for e in entities if e.get("type") in ("Database", "Library", "Service")]
        lines.append("## Tech Stack\n" + "\n".join(f"- {t}" for t in tech_stack))
        return "\n".join(lines)

    if section == "apis":
        decisions = memory.get("decisions", [])
        lines = ["# API Decisions\n"]
        for d in decisions:
            text = d.get("text", str(d))
            rationale = d.get("rationale", "")
            conf = d.get("confidence", 0.0)
            lines.append(f"- **{text}**\n  - Rationale: {rationale}\n  - Confidence: {conf:.0%}")
        return "\n".join(lines)

    if section == "database":
        entities = memory.get("entities", [])
        dbs = [e.get("name", str(e)) for e in entities if e.get("type") == "Database"]
        lines = ["# Database\n"] + [f"- {db}" for db in dbs]
        return "\n".join(lines)

    if section == "constraints":
        constraints = memory.get("constraints", [])
        lines = ["# Constraints\n"]
        for c in constraints:
            text = c.get("text", str(c))
            conf = c.get("confidence", 0.0)
            lines.append(f"- [ ] {text} *(conf: {conf:.0%})*")
        return "\n".join(lines)

    if section == "tasks" or section == "current_progress":
        tasks = memory.get("tasks", [])
        title = "# Current Progress\n" if section == "current_progress" else "# Tasks\n"
        lines = [title]
        for t in tasks:
            text = t.get("text", str(t))
            status = t.get("status", "pending")
            checked = "x" if status == "done" else " "
            lines.append(f"- [{checked}] {text}")
        return "\n".join(lines)

    if section == "coding_style":
        return "# Coding Style\n- Strict TypeScript — no implicit `any`\n- Tailwind CSS utility-first\n- React functional components only"

    return f"# {section.title()}\n*No data available.*"


async def compile_pack(
    conversation_id: str,
    role_pack: str,
    selections: dict[str, bool],
) -> dict[str, Any]:
    """
    Main entry point. Compiles a Smart Context Pack from Neo4j memory.
    Returns the pack_id and compiled markdown file map.
    """
    memory = await _fetch_project_memory(conversation_id)
    template_sections = PACK_TEMPLATES.get(role_pack, ["architecture", "constraints"])

    if role_pack == "backend":
        import os
        template_path = os.path.join(os.path.dirname(__file__), "templates", "ULTIMATE_CONTEXT_PACK.md")
        try:
            with open(template_path, encoding="utf-8") as f:
                content = f.read()
        except Exception:
            content = "# ContextOS Backend Context Pack\n\nTemplate not found."

        # Dynamically append Neo4j graph data
        content += "\n\n====================================================\n"
        content += "DYNAMIC NEO4J CONTEXT\n"
        content += "====================================================\n\n"
        
        content += _compile_section("architecture", memory) + "\n\n"
        content += _compile_section("apis", memory) + "\n\n"
        content += _compile_section("constraints", memory) + "\n\n"
        content += _compile_section("current_progress", memory) + "\n\n"

        files = {"Ultimate-Context-Pack.md": content}
    else:
        # Filter to only sections explicitly selected by the user for other roles
        active_sections = [s for s in template_sections if selections.get(s, True)]
        files: dict[str, str] = {}
        for section in active_sections:
            filename = f"{section.replace('_', '-').title()}.md"
            files[filename] = _compile_section(section, memory)

    pack_id = f"pack_{uuid.uuid4().hex[:8]}"

    # Persist the ContextPack node in Neo4j
    if not settings.MOCK_MODE:
        async with get_session() as session:
            await session.run(
                """
                MERGE (p:ContextPack {id: $id})
                SET p.role_pack = $role_pack, p.created_at = timestamp()
                WITH p
                MATCH (c:Conversation {id: $conv_id})
                MERGE (c)-[:GENERATED]->(p)
                """,
                id=pack_id, role_pack=role_pack, conv_id=conversation_id,
            )

    return {"pack_id": pack_id, "role_pack": role_pack, "files": files}
