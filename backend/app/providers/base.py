"""
Universal Memory Provider Architecture

This module defines the base interface for all Memory Providers.
Every external system (Genesis Kit, Git, Linear, Notion, ChatGPT) must implement
this adapter pattern to convert their native state into ContextBridge Memory Objects.
"""
from abc import ABC, abstractmethod
from typing import Any
from datetime import datetime

class MemoryObject:
    def __init__(self, source_id: str, provider_name: str, content: str, metadata: dict[str, Any] | None = None):
        self.source_id = source_id
        self.provider_name = provider_name
        self.content = content
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()

class BaseMemoryProvider(ABC):
    """
    The core contract for all ContextBridge integrations.
    """
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider (e.g., 'genesis', 'git', 'linear')."""
        pass

    @abstractmethod
    async def fetch_state(self) -> dict[str, Any]:
        """
        Connects to the external source and retrieves the raw state.
        """
        pass

    @abstractmethod
    def parse_to_memory_objects(self, raw_state: dict[str, Any]) -> list[MemoryObject]:
        """
        Converts the raw state into agnostic ContextBridge Memory Objects.
        """
        pass

    async def ingest(self) -> list[MemoryObject]:
        """
        The standard pipeline: fetch -> parse -> return canonical objects.
        """
        raw = await self.fetch_state()
        return self.parse_to_memory_objects(raw)
