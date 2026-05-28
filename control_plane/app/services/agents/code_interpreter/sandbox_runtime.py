# Owner: agent-platform
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.agent_tool_synthesis import AgentCodeInterpreterRun, AgentSandboxSession

from .microvm_policy import MicroVMPolicy
from .providers.docker_sandbox import DockerSandboxProvider
from .providers.firecracker_sandbox import FirecrackerSandboxProvider
from .providers.gvisor_sandbox import GVisorSandboxProvider
from .providers.mock_sandbox import MockSandboxProvider
from .providers.wasm_sandbox import WasmSandboxProvider
from .sandbox_artifacts import SandboxArtifactService
from .sandbox_attestation import AttestationService
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
        self.microvm_policy = MicroVMPolicy(self.settings)
        self.attestation_service = AttestationService()

    def _get_provider(self):
        provider_name = self.microvm_policy.resolve_provider_name()
        self.microvm_policy.ensure_provider_enabled(provider_name)
        providers = {
            "docker": DockerSandboxProvider,
            "wasm": WasmSandboxProvider,
            "firecracker": FirecrackerSandboxProvider,
            "gvisor": GVisorSandboxProvider,
            "mock": MockSandboxProvider,
        }
        return providers[provider_name]()

    async def check_readiness(self) -> dict[str, Any]:
        try:
            self._get_provider()
            report = self.microvm_policy.readiness_report()
        except Exception as exc:
            provider = self.settings.agent_code_sandbox_provider
            report = {
                "provider": provider,
                "sandbox_provider_available": False,
                "provider_configured": False,
                "provider_healthy": False,
                "microvm_required": self.settings.agent_code_sandbox_microvm_required,
                "fallback_allowed": not self.settings.agent_code_sandbox_microvm_required,
                "fallback_blocked": self.settings.agent_code_sandbox_microvm_required,
                "error": str(exc),
            }
        return report

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
        profile = self.microvm_policy.build_isolation_profile(provider.name, result["limits"])
        for field_name in ("kernel_isolation_level", "network_mode", "filesystem_mode"):
            value = result.get(field_name)
            if not value:
                raise RuntimeError(f"Sandbox provider {provider.name} did not report {field_name} for attestation")
            setattr(profile, field_name, value)
        attestation = self.attestation_service.create_attestation(
            profile=profile,
            code=code,
            stdout=result["stdout"],
            stderr=result["stderr"],
            artifacts=result.get("artifacts"),
        )
        result["attestation"] = attestation.model_dump(mode="json")
        if not self.attestation_service.verify_attestation(result["attestation"]):
            raise RuntimeError(f"Sandbox provider {provider.name} failed attestation verification")
        if self.settings.app_env == "production" and not result.get("attestation"):
            raise RuntimeError(f"Sandbox provider {provider.name} failed to provide attestation in production")
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
        run.__dict__["attestation"] = result.get("attestation")
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
