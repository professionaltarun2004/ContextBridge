"""
Genesis Kit Provider Adapter

Responsible for parsing `.genesis/` project structures and converting
them into agnostic ContextBridge Memory Objects.
"""
import os
import json
from pathlib import Path
from typing import Any
from .base import BaseMemoryProvider, MemoryObject

class GenesisAdapter(BaseMemoryProvider):
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.genesis_dir = self.repo_path / ".genesis"

    @property
    def provider_name(self) -> str:
        return "genesis"

    async def fetch_state(self) -> dict[str, Any]:
        """
        Reads the local .genesis directory and extracts the core files.
        """
        state: dict[str, Any] = {}
        
        if not self.genesis_dir.exists():
            return state

        # Read PLAN.md
        plan_path = self.genesis_dir / "PLAN.md"
        if plan_path.exists():
            state["plan"] = plan_path.read_text(encoding="utf-8")
            
        # Read CURRENT.md
        current_path = self.genesis_dir / "CURRENT.md"
        if current_path.exists():
            state["current"] = current_path.read_text(encoding="utf-8")

        # Read context-graph.json
        graph_path = self.genesis_dir / "context-graph.json"
        if graph_path.exists():
            try:
                state["graph"] = json.loads(graph_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        return state

    def parse_to_memory_objects(self, raw_state: dict[str, Any]) -> list[MemoryObject]:
        """
        Converts the raw Genesis files into structured memory objects.
        """
        objects = []
        
        if "plan" in raw_state:
            objects.append(MemoryObject(
                source_id="genesis:plan",
                provider_name=self.provider_name,
                content=f"Project Plan & Milestones:\n{raw_state['plan']}",
                metadata={"type": "milestone_tracker"}
            ))

        if "current" in raw_state:
            objects.append(MemoryObject(
                source_id="genesis:current",
                provider_name=self.provider_name,
                content=f"Current Sprint & State:\n{raw_state['current']}",
                metadata={"type": "current_state"}
            ))

        if "graph" in raw_state:
            objects.append(MemoryObject(
                source_id="genesis:graph",
                provider_name=self.provider_name,
                content=json.dumps(raw_state["graph"]),
                metadata={"type": "knowledge_graph"}
            ))

        return objects
