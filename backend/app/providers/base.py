"""
Universal Memory Provider Architecture (Drivers)

This module defines the base interface for all Memory Providers.
Every external system (Genesis Kit, Git, Linear, Notion, ChatGPT) must implement
this adapter pattern to convert their native state into the Kernel's Memory Objects.
"""
from abc import ABC, abstractmethod
from typing import Any

from app.kernel.memory import MemoryObject


class BaseMemoryProvider(ABC):
    """
    The core driver contract for all ContextBridge integrations.
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
        Converts the raw state into agnostic Kernel Memory Objects.
        """
        pass

    async def ingest(self) -> list[MemoryObject]:
        """
        The standard pipeline: fetch -> parse -> return canonical objects.
        """
        raw = await self.fetch_state()
        return self.parse_to_memory_objects(raw)
