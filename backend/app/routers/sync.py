"""
POST /api/v1/sync — Sync conversation, generate embeddings, return summary.
GET  /api/v1/context — Semantic vector search for historical context.
FR-005: Cloud-synced vector memory vault.
FR-003: Summarization integrated into sync flow.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthTokenClaims, require_subscription
from app.database import get_db
from app.models import Conversation, User, VectorChunk
from app.schemas import (
    ContextMatch,
    MatchContextResponse,
    SyncRequestPayload,
    SyncResponsePayload,
)
from app.summarizer import generate_embeddings, generate_summary

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/sync",
    response_model=SyncResponsePayload,
    status_code=status.HTTP_201_CREATED,
    summary="Sync conversation and generate vector summary",
    description=(
        "Accepts a sanitized conversation payload from the extension, "
        "generates embeddings, stores them, and returns a summarized context block."
    ),
)
async def sync_conversation(
    payload: SyncRequestPayload,
    auth: AuthTokenClaims = Depends(require_subscription),
    db: AsyncSession = Depends(get_db),
) -> SyncResponsePayload:
    """
    Sync flow:
    1. Upsert user record.
    2. Create conversation record with raw_chat_history.
    3. Generate LLM summary with the selected preset.
    4. Generate vector embeddings from the summary.
    5. Store VectorChunk.
    6. Return summary and conversation ID.
    """
    # 1. Ensure user record exists (RLS: auth.sub == user.id always)
    result = await db.execute(select(User).where(User.id == auth.sub))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(id=auth.sub, email=auth.email, is_subscribed=True)
        db.add(user)
        await db.flush()

    # 2. Persist conversation with raw history
    messages_dicts = [m.model_dump() for m in payload.messages]
    conversation = Conversation(
        user_id=auth.sub,
        source_platform=payload.source_platform,
        raw_chat_history={"messages": messages_dicts},
    )
    db.add(conversation)
    await db.flush()

    # 3. Generate AI summary
    try:
        summary = await generate_summary(messages_dicts, preset=payload.preset.value)
    except Exception as exc:
        logger.error("Summarization failed for user %s: %s", auth.sub, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Summarization service temporarily unavailable.",
        ) from exc

    # 4. Generate embeddings
    try:
        embedding = await generate_embeddings(summary)
    except Exception as exc:
        logger.error("Embedding generation failed for user %s: %s", auth.sub, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedding service temporarily unavailable.",
        ) from exc

    # 5. Store VectorChunk
    chunk = VectorChunk(
        conversation_id=conversation.id,
        embedding=embedding,
        summary_text=summary,
    )
    db.add(chunk)

    logger.info(
        "Synced conversation %s for user %s (platform=%s, messages=%d)",
        conversation.id,
        auth.sub,
        payload.source_platform,
        len(payload.messages),
    )

    return SyncResponsePayload(
        conversation_id=str(conversation.id),
        summary_text=summary,
        preset_applied=payload.preset.value,
    )


@router.get(
    "/context",
    response_model=MatchContextResponse,
    summary="Semantic context lookup",
    description=(
        "Generates a query embedding and performs cosine similarity search "
        "against the user's stored vector chunks."
    ),
)
async def get_context(
    q: str,
    limit: int = 3,
    auth: AuthTokenClaims = Depends(require_subscription),
    db: AsyncSession = Depends(get_db),
) -> MatchContextResponse:
    """
    Context retrieval flow:
    1. Generate embedding from the query string.
    2. Cosine similarity search against user's vector chunks via pgvector.
    3. Return top matches with similarity scores.
    Row-level security: WHERE clause always filters by auth.sub.
    """
    if not q.strip():
        return MatchContextResponse(matches=[])

    if limit < 1 or limit > 10:
        limit = 3

    try:
        query_embedding = await generate_embeddings(q)
    except Exception as exc:
        logger.error("Query embedding failed for user %s: %s", auth.sub, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedding service temporarily unavailable.",
        ) from exc

    # Cosine similarity search using pgvector operator <=>
    # RLS: join on conversations.user_id = auth.sub
    stmt = text(
        """
        SELECT
            vc.id,
            vc.summary_text,
            1 - (vc.embedding <=> CAST(:query_embedding AS vector)) AS similarity_score
        FROM vector_chunks vc
        JOIN conversations c ON c.id = vc.conversation_id
        WHERE c.user_id = :user_id
        ORDER BY vc.embedding <=> CAST(:query_embedding AS vector)
        LIMIT :limit
        """
    )

    result = await db.execute(
        stmt,
        {
            "query_embedding": str(query_embedding),
            "user_id": auth.sub,
            "limit": limit,
        },
    )
    rows = result.fetchall()

    matches = [
        ContextMatch(
            chunk_id=str(row[0]),
            summary_text=row[1],
            similarity_score=float(row[2]),
        )
        for row in rows
    ]

    logger.debug(
        "Context query for user %s returned %d matches", auth.sub, len(matches)
    )

    return MatchContextResponse(matches=matches)
