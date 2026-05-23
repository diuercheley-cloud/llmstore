from typing import Any, Dict, List, Tuple
from kleberai.agents.adapters import PlannerProviderV1, AdapterManifest

class SimplePlanner(PlannerProviderV1):
    async def manifest(self) -> AdapterManifest:
        return AdapterManifest(
            id="simple-planner",
            name="Simple Sequence Planner",
            version="1.0.0",
            compatibility_version="v1"
        )

    async def schema(self) -> Dict[str, Any]:
        return {}

    async def healthcheck(self) -> bool:
        return True

    async def dry_run(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        return True, "OK"

    async def plan(self, goal: str, available_tools: List[str], history: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Dumb planner: just calls the first tool if available
        if not available_tools:
            return {"tasks": [], "status": "failed", "reason": "No tools"}
        
        return {
            "goal": goal,
            "tasks": [
                {"tool": available_tools[0], "input": {"query": goal}}
            ],
            "requires_approval": False
        }
