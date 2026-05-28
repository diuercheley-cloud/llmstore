# Owner: agent-platform
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.agent_tool_synthesis import AgentCodeInterpreterRun, AgentSandboxSession

from .providers.docker_sandbox import DockerSandboxProvider
from .providers.mock_sandbox import MockSandboxProvider
from .providers.wasm_sandbox import WasmSandboxProvider
from .sandbox_artifacts import SandboxArtifactService
from .sandbox_audit import SandboxAuditService
from .sandbox_limits import SandboxLimits
from .sandbox_policy import SandboxPolicyEngine, SandboxPolicyViolation


class SandboxRuntime:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.policy = SandboxPolicyEngine()
        self.limits = SandboxLimits()
        self.audit = SandboxAuditService(db)
        self.artifacts = SandboxArtifactService(db)

    def _get_provider(self):
        provider_name = self.settings.agent_code_sandbox_provider
        if provider_name == "docker":
            if not self.settings.agent_code_sandbox_docker_enabled:
                raise RuntimeError("Docker sandbox provider is disabled by feature flag")
            return DockerSandboxProvider()
        if provider_name == "wasm":
            if not self.settings.agent_code_sandbox_wasm_enabled:
                raise RuntimeError("WASM sandbox provider is disabled by feature flag")
            return WasmSandboxProvider()
        return MockSandboxProvider()

    async def execute(
        self,
        code: str,
        session_id: uuid.UUID | None = None,
        agent_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        decisions = self.policy.validate_code(code)
        limits = self.limits.get_defaults()
        provider = self._get_provider()
        result = await provider.run(code=code, limits=limits, session_id=session_id)
        result["limits"] = limits.model_dump()
        result["policy_decisions"] = [decision.__dict__ for decision in decisions]
        result["provider"] = provider.name
        result["mock"] = getattr(provider, "mock", False)
        result["stdout"], result["stdout_truncated"] = self.policy.truncate_output(
            result.get("stdout", ""),
            limits.max_output_size_bytes,
        )
        result["stderr"], result["stderr_truncated"] = self.policy.truncate_output(
            result.get("stderr", ""),
            limits.max_output_size_bytes,
        )
        return result

    async def persist_run(
        self,
        code: str,
        result: dict[str, Any],
        session_id: uuid.UUID | None = None,
        agent_id: uuid.UUID | None = None,
    ) -> AgentCodeInterpreterRun:
        run = AgentCodeInterpreterRun(
            session_id=session_id,
            agent_id=agent_id,
            code=code,
            stdout=result.get("stdout"),
            stderr=result.get("stderr"),
            exit_code=result.get("exit_code"),
            execution_time_ms=result.get("execution_time_ms"),
        )
        self.db.add(run)
        await self.db.commit()
        await self.db.refresh(run)
        run.__dict__["provider"] = result.get("provider")
        run.__dict__["policy_decisions"] = result.get("policy_decisions", [])
        run.__dict__["limits"] = result.get("limits", {})
        run.__dict__["mock"] = result.get("mock", False)
        return run

    async def ensure_session(self, session_id: uuid.UUID | None, agent_id: uuid.UUID | None = None) -> AgentSandboxSession:
        if session_id is not None:
            session = await self.db.get(AgentSandboxSession, session_id)
            if session is None:
                raise SandboxPolicyViolation("Sandbox session not found", {"session_id": str(session_id)})
            return session
        session = AgentSandboxSession(agent_id=agent_id, status="active")
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session
