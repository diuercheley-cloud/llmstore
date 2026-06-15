# Owner: agent-platform
import time
import uuid
from typing import Any


class WasmSandboxProvider:
    name = "wasm"
    mock = False

    async def run(
        self, code: str, limits: Any, session_id: uuid.UUID | None = None
    ) -> dict[str, Any]:
        started_at = time.time()
        return {
            "stdout": "",
            "stderr": "WASM sandbox provider is registered but experimental. Enable a WASI runtime before production use.",
            "exit_code": 126,
            "execution_time_ms": int((time.time() - started_at) * 1000),
            "provider": self.name,
            "mock": False,
            "experimental": True,
            "artifacts": [],
            "limits": limits.model_dump(),
        }
