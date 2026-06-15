# Owner: agent-platform
import ast
import time
import uuid
from typing import Any


class MockSandboxProvider:
    name = "mock"
    mock = True

    async def run(
        self, code: str, limits: Any, session_id: uuid.UUID | None = None
    ) -> dict[str, Any]:
        start_time = time.time()
        stdout_lines: list[str] = []
        for node in ast.walk(ast.parse(code)):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "print"
            ):
                values: list[str] = []
                for arg in node.args:
                    if isinstance(arg, ast.Constant):
                        values.append(str(arg.value))
                    else:
                        values.append("<expr>")
                stdout_lines.append(" ".join(values))
        if "while True" in code or "time.sleep(" in code:
            return {
                "stdout": "",
                "stderr": f"Execution timed out after {limits.timeout_seconds} seconds.",
                "exit_code": 124,
                "execution_time_ms": int((time.time() - start_time) * 1000),
                "provider": self.name,
                "simulated": True,
                "mock": True,
                "kernel_isolation_level": "simulated",
                "network_mode": "none",
                "filesystem_mode": "simulated-read-only",
                "artifacts": [],
            }
        return {
            "stdout": ("\n".join(stdout_lines) + ("\n" if stdout_lines else "")),
            "stderr": "",
            "exit_code": 0,
            "execution_time_ms": int((time.time() - start_time) * 1000),
            "provider": self.name,
            "simulated": True,
            "mock": True,
            "kernel_isolation_level": "simulated",
            "network_mode": "none",
            "filesystem_mode": "simulated-read-only",
            "artifacts": [],
        }
