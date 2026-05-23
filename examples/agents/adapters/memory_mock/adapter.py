import uuid
from typing import Any, Dict, List, Tuple
from kleberai.agents.adapters import MemoryProviderV1, AdapterManifest

class MockMemory(MemoryProviderV1):
    def __init__(self):
        self._data = {}

    async def manifest(self) -> AdapterManifest:
        return AdapterManifest(
            id="mock-memory",
            name="Mock Memory Provider",
            version="1.0.0",
            compatibility_version="v1"
        )

    async def schema(self) -> Dict[str, Any]:
        return {}

    async def healthcheck(self) -> bool:
        return True

    async def dry_run(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        return True, "OK"

    async def store(self, agent_id: uuid.UUID, run_id: uuid.UUID, item: Dict[str, Any]) -> bool:
        key = f"{agent_id}:{run_id}"
        if key not in self._data:
            self._data[key] = []
        self._data[key].append(item)
        return True

    async def retrieve(self, agent_id: uuid.UUID, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        # In a mock, we just return everything for the agent
        results = []
        for key, items in self._data.items():
            if str(agent_id) in key:
                results.extend(items)
        return results[:limit]
