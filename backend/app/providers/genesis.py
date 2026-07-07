"""
Genesis Kit Provider Adapter (Driver)

Responsible for parsing `.genesis/` project structures and converting
them into agnostic ContextBridge Memory Objects using the Kernel ABI.
"""
import json
from pathlib import Path
from typing import Any

from app.providers.base import BaseMemoryProvider
from app.kernel.memory import MemoryObject, MemoryType

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
                type=MemoryType.GOAL,
                title="Project Plan & Milestones",
                content=raw_state["plan"],
                source="genesis://PLAN.md",
                importance=0.9
            ))

        if "current" in raw_state:
            objects.append(MemoryObject(
                type=MemoryType.CHECKPOINT,
                title="Current Sprint State",
                content=raw_state["current"],
                source="genesis://CURRENT.md",
                freshness=1.0,
                importance=1.0
            ))

        if "graph" in raw_state:
            objects.append(MemoryObject(
                type=MemoryType.ARCHITECTURE,
                title="Genesis Knowledge Graph",
                content=json.dumps(raw_state["graph"]),
                source="genesis://context-graph.json"
            ))

        return objects
