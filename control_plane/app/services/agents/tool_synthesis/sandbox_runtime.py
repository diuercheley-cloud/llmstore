import time
import uuid

from app.models.agent_tool_synthesis import AgentCodeInterpreterRun
from app.services.agents.code_interpreter.providers.mock_sandbox import MockSandboxProvider
from app.services.agents.code_interpreter.sandbox_limits import SandboxLimits
from app.services.agents.code_interpreter.sandbox_policy import SandboxPolicyEngine


class SandboxRuntime:
    def __init__(self, db, allow_network: bool = False, allow_write: bool = False):
        self.db = db
        self.allow_network = allow_network
        self.allow_write = allow_write
        self.policy = SandboxPolicyEngine()
        self.provider = MockSandboxProvider()
        self.limits = SandboxLimits()

    def execute_code(
        self,
        session_id: uuid.UUID,
        code: str,
        agent_id: uuid.UUID | None = None,
        timeout_seconds: int = 5,
    ) -> AgentCodeInterpreterRun:
        self.policy.validate_code(code)
        started_at = time.time()
        result = self._run_mock(code, timeout_seconds=timeout_seconds)
        stdout, _ = self.policy.truncate_output(result["stdout"], self.limits.get_defaults().max_output_size_bytes)
        stderr, _ = self.policy.truncate_output(result["stderr"], self.limits.get_defaults().max_output_size_bytes)
        run = AgentCodeInterpreterRun(
            session_id=session_id,
            agent_id=agent_id,
            code=code,
            stdout=stdout,
            stderr=stderr,
            exit_code=result["exit_code"],
            execution_time_ms=int((time.time() - started_at) * 1000),
        )
        if hasattr(self.db, "add"):
            self.db.add(run)
        if hasattr(self.db, "commit"):
            self.db.commit()
        if hasattr(self.db, "refresh"):
            self.db.refresh(run)
        return run

    def _run_mock(self, code: str, timeout_seconds: int) -> dict[str, str | int]:
        if "while True" in code:
            return {
                "stdout": "",
                "stderr": f"Execution timed out after {timeout_seconds} seconds.",
                "exit_code": 124,
            }
        stdout = ""
        if "print(" in code:
            stdout = "hello world\n" if "hello world" in code else "mock execution completed\n"
        return {"stdout": stdout, "stderr": "", "exit_code": 0}
