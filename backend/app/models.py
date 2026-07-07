"""
SQLAlchemy ORM Models for ContextBridge.
Implements: User, Conversation, VectorChunk entities from the Solution data model.
pgvector VECTOR type is used for 1536-dimensional embeddings (OpenAI text-embedding-3-small).
"""

from __future__ import annotations

import uuid
from datetime import datetime

# pgvector SQLAlchemy integration
from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class User(Base):
    """
    User entity — maps Auth0 identity to billing status.
    Fields match the solution schema exactly.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
        comment="Auth0 sub claim (UUID-formatted identifier)",
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True
    )
    is_subscribed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    conversations: Mapped[list[Conversation]] = relationship(
        "Conversation", back_populates="user", cascade="all, delete-orphan"
    )


class Conversation(Base):
    """
    Transient conversation entity.
    raw_chat_history is purged after 24 hours; VectorChunks persist indefinitely.
    """

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    source_platform: Mapped[str] = mapped_column(
        String(50), nullable=False
    )
    raw_chat_history: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="Purged after 24 hours by the purge daemon"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship("User", back_populates="conversations")
    vector_chunks: Mapped[list[VectorChunk]] = relationship(
        "VectorChunk",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_conversations_user_id_created_at", "user_id", "created_at"),
    )


class VectorChunk(Base):
    """
    Long-term semantic summary stored as a 1536-dimensional vector.
    Indexed with HNSW cosine distance for fast similarity search.
    Persists after raw conversation data is purged.
    """

    __tablename__ = "vector_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    embedding: Mapped[list[float]] = mapped_column(
        Vector(1536), nullable=False, comment="OpenAI text-embedding-3-small output"
    )
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    conversation: Mapped[Conversation] = relationship(
        "Conversation", back_populates="vector_chunks"
    )

    # HNSW index for fast cosine distance search — created via Alembic migration
    # __table_args__ includes this via migration; not declarable inline for HNSW
