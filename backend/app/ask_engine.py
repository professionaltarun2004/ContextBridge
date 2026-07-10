"""
ContextOS — Graph Traversal "Ask" Engine (FR-009)
Natural language question answering over the Neo4j Knowledge Graph.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, cast

from litellm import acompletion as _acompletion  # type: ignore[import-untyped]

from app.config import settings
from app.database import get_session

acompletion = cast(Callable[..., Any], _acompletion)
logger = logging.getLogger(__name__)

MOCK_ASK_RESPONSE = {
    "answer": (
        "FastAPI was chosen because it is an async-native, high-concurrency framework "
        "that integrates natively with Pydantic for strict schema validation and auto-generated "
        "OpenAPI documentation, making it ideal for the ContextOS backend gateway."
    ),
    "confidence_average": 0.98,
    "citations": [
        {
            "node_id": "dec_mock_0",
            "node_label": "Decision",
            "source_message": "msg_42",
            "source_ai": "Claude",
            "conversation_id": "conv_mock",
        }
    ],
}


async def _traverse_graph(question: str) -> list[dict[str, Any]]:
    """
    Queries Neo4j for nodes relevant to the question.
    Performs a simple keyword-based traversal for V1.
    """
    # Extract key terms from the question (naive keyword approach for V1)
    keywords = [w for w in question.lower().split() if len(w) > 3]
    found_nodes: list[dict[str, Any]] = []

    async with get_session() as session:
        for keyword in keywords[:5]:  # Limit traversal depth
            result = await session.run(
                """
                MATCH (n)
                WHERE toLower(n.text) CONTAINS $kw OR toLower(n.name) CONTAINS $kw
                RETURN n, labels(n) AS label LIMIT 5
                """,
                kw=keyword,
            )
            async for record in result:
                node = dict(record["n"])
                node["_label"] = record["label"][0] if record["label"] else "Unknown"
                found_nodes.append(node)

    return found_nodes


async def traverse_and_answer(question: str) -> dict[str, Any]:
    """
    Main entry point. Traverses the graph and synthesizes an answer.
    """
    if settings.MOCK_MODE:
        logger.info("MOCK_MODE: returning fixture Ask response.")
        return MOCK_ASK_RESPONSE

    nodes = await _traverse_graph(question)

    if not nodes:
        return {
            "answer": "No relevant context found in the Knowledge Graph for that question.",
            "confidence_average": 0.0,
            "citations": [],
        }

    # Build context for LLM synthesis
    context_block = "\n".join(
        f"[{n.get('_label')}] {n.get('text', n.get('name', 'Unknown'))} "
        f"(confidence: {n.get('confidence', 0.5):.0%})"
        for n in nodes[:10]
    )

    prompt = (
        f"You are a developer assistant with access to a project knowledge graph.\n"
        f"Answer the following question based ONLY on the graph context provided.\n"
        f"Be concise and cite confidence scores.\n\n"
        f"Question: {question}\n\n"
        f"Graph Context:\n{context_block}"
    )

    try:
        response = await acompletion(
            model="gemini/gemini-pro",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=400,
            api_key=settings.GEMINI_API_KEY,
        )
        answer = response.choices[0].message.content or "Unable to synthesize answer."
    except Exception as exc:
        logger.warning("LLM synthesis failed: %s", exc)
        answer = f"Graph found {len(nodes)} relevant nodes but LLM synthesis failed."

    avg_confidence = (
        sum(n.get("confidence", 0.5) for n in nodes) / len(nodes) if nodes else 0.0
    )

    citations = [
        {
            "node_id": n.get("id", "unknown"),
            "node_label": n.get("_label", "Unknown"),
            "source_message": n.get("source_message", ""),
            "source_ai": n.get("source_ai", ""),
            "conversation_id": n.get("conversation_id", ""),
        }
        for n in nodes[:5]
    ]

    return {
        "answer": answer,
        "confidence_average": round(avg_confidence, 3),
        "citations": citations,
    }
