# Owner: agent-platform
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings

from .sandbox_audit import SandboxAuditService
from .sandbox_runtime import SandboxRuntime


class CodeInterpreter:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.runtime = SandboxRuntime(db)
        self.audit = SandboxAuditService(db)

    async def run_code(
        self,
        code: str,
        agent_id: uuid.UUID | None = None,
        run_id: uuid.UUID | None = None,
        tenant_id: str | None = None,
        session_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        if not self.settings.agent_code_interpreter_enabled:
            raise RuntimeError("Code Interpreter is disabled by feature flag.")

        session = await self.runtime.ensure_session(session_id, agent_id=agent_id)
        limits = self.runtime.limits.get_defaults()
        provider = self.runtime._get_provider()
        await self.audit.record_start(
            agent_id=agent_id,
            run_id=run_id,
            tenant_id=tenant_id,
            code=code,
            session_id=session.id,
            provider=provider.name,
            limits=limits.model_dump(),
        )
        result = await self.runtime.execute(code=code, session_id=session.id, agent_id=agent_id)
        persisted = await self.runtime.persist_run(
            code=code,
            result=result,
            session_id=session.id,
            agent_id=agent_id,
        )
        await self.audit.record_event(
            "execution_finished",
            {
                "run_id": str(persisted.id),
                "provider": result.get("provider"),
                "exit_code": result.get("exit_code"),
                "execution_time_ms": result.get("execution_time_ms"),
                "limits": result.get("limits"),
                "policy_decisions": result.get("policy_decisions"),
            },
            session_id=session.id,
        )
        response = {
            "run_id": str(persisted.id),
            "session_id": str(session.id),
            **result,
        }
        return response
