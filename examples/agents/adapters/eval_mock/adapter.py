import uuid
from typing import Any, Dict, List, Tuple
from kleberai.agents.adapters import EvalProviderV1, AdapterManifest

class MockEval(EvalProviderV1):
    async def manifest(self) -> AdapterManifest:
        return AdapterManifest(
            id="mock-eval",
            name="Mock Evaluation Provider",
            version="1.0.0",
            compatibility_version="v1"
        )

    async def schema(self) -> Dict[str, Any]:
        return {}

    async def healthcheck(self) -> bool:
        return True

    async def dry_run(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        return True, "OK"

    async def evaluate(self, run_id: uuid.UUID, criteria: List[str]) -> Dict[str, Any]:
        return {
            "run_id": str(run_id),
            "score": 0.95,
            "passed": True,
            "details": {c: "Passed" for c in criteria}
        }
