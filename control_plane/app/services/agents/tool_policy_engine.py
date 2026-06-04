# Owner: agent-platform
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from app.core.time import utc_now
from app.models.commercial_agents import (
    CommercialAgentAction,
    CommercialAgentExecution,
    CommercialAgentProfile,
    CommercialToolRegistry,
)
from app.services.agents.execution_receipts import (
    canonical_json,
    redact_confidential_payload,
    sha256_hex,
)
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class PolicyDecision:
    allowed: bool
    decision: str
    reason: str
    requires_approval: bool = False
    tool: CommercialToolRegistry | None = None
    sanitized_payload: Any = None
    payload_hash: str | None = None


class ToolPolicyEngine:
    async def resolve_tool_registration(
        self,
        db: AsyncSession,
        *,
        tool_name: str,
        tenant_id: str,
    ) -> CommercialToolRegistry | None:
        result = await db.execute(
            select(CommercialToolRegistry)
            .where(
                CommercialToolRegistry.tool_name == tool_name,
                or_(CommercialToolRegistry.tenant_id == tenant_id, CommercialToolRegistry.tenant_id.is_(None)),
                CommercialToolRegistry.enabled.is_(True),
            )
            .order_by(CommercialToolRegistry.tenant_id.desc())
        )
        return result.scalars().first()

    async def evaluate_action(
        self,
        db: AsyncSession,
        *,
        profile: CommercialAgentProfile,
        execution: CommercialAgentExecution,
        tool_name: str,
        payload: Any,
        dry_run: bool = False,
    ) -> PolicyDecision:
        payload_hash = sha256_hex(canonical_json(payload))
        registration = await self.resolve_tool_registration(
            db,
            tool_name=tool_name,
            tenant_id=execution.tenant_id or profile.client_id or "",
        )
        if registration is None:
            return PolicyDecision(
                allowed=False,
                decision="denied",
                reason="tool_not_registered",
                sanitized_payload=redact_confidential_payload(payload),
                payload_hash=payload_hash,
            )
        if registration.trust_status not in {"trusted", "approved"}:
            return PolicyDecision(
                allowed=False,
                decision="denied",
                reason="tool_not_trusted",
                tool=registration,
                sanitized_payload=redact_confidential_payload(payload, mode=registration.confidential_payload_mode),
                payload_hash=payload_hash,
            )

        tenant_id = execution.tenant_id or ""
        if registration.tenant_id and registration.tenant_id != tenant_id:
            return PolicyDecision(False, "denied", "tenant_scope_mismatch", tool=registration, payload_hash=payload_hash)

        if profile.client_id and tenant_id and profile.client_id != tenant_id:
            return PolicyDecision(False, "denied", "agent_profile_tenant_mismatch", tool=registration, payload_hash=payload_hash)

        allowed_tenants = profile.allowed_tenants_json or []
        if allowed_tenants and tenant_id not in allowed_tenants:
            return PolicyDecision(False, "denied", "tenant_not_permitted", tool=registration, payload_hash=payload_hash)

        allowed_tools = profile.allowed_tools or []
        if tool_name not in allowed_tools and "*" not in allowed_tools:
            return PolicyDecision(False, "denied", "tool_not_in_agent_allowlist", tool=registration, payload_hash=payload_hash)

        quota_ok, quota_reason = await self._check_quota_limits(
            db,
            profile=profile,
            tenant_id=tenant_id,
            tool=registration,
        )
        if not quota_ok:
            return PolicyDecision(False, "denied", quota_reason, tool=registration, payload_hash=payload_hash)

        sanitized_payload = redact_confidential_payload(payload, mode=registration.confidential_payload_mode)

        if dry_run and not registration.allow_dry_run:
            return PolicyDecision(False, "denied", "dry_run_not_permitted", tool=registration, sanitized_payload=sanitized_payload, payload_hash=payload_hash)

        requires_approval = bool(profile.requires_approval_for_tools or registration.requires_approval)
        decision = "pending_approval" if requires_approval and not dry_run else "allowed"
        reason = "approval_required" if requires_approval and not dry_run else ("dry_run" if dry_run else "policy_allow")
        return PolicyDecision(
            allowed=True,
            decision=decision,
            reason=reason,
            requires_approval=requires_approval and not dry_run,
            tool=registration,
            sanitized_payload=sanitized_payload,
            payload_hash=payload_hash,
        )

    async def summarize_policy_violations(
        self,
        db: AsyncSession,
        *,
        tenant_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        stmt = (
            select(CommercialAgentAction)
            .where(CommercialAgentAction.status == "denied")
            .order_by(CommercialAgentAction.executed_at.desc())
            .limit(limit)
        )
        if tenant_id:
            stmt = stmt.where(CommercialAgentAction.tenant_id == tenant_id)
        rows = (await db.execute(stmt)).scalars().all()
        return [
            {
                "id": str(row.id),
                "execution_id": str(row.execution_id),
                "tenant_id": row.tenant_id,
                "tool_name": row.tool_name,
                "reason": (row.policy_decision_json or {}).get("reason"),
                "created_at": row.executed_at.isoformat() if row.executed_at else None,
            }
            for row in rows
        ]

    async def _check_quota_limits(
        self,
        db: AsyncSession,
        *,
        profile: CommercialAgentProfile,
        tenant_id: str,
        tool: CommercialToolRegistry,
    ) -> tuple[bool, str]:
        minute_start = utc_now() - timedelta(minutes=1)
        day_start = utc_now() - timedelta(days=1)

        minute_total = await db.scalar(
            select(func.count(CommercialAgentAction.id)).where(
                CommercialAgentAction.tenant_id == tenant_id,
                CommercialAgentAction.tool_name == tool.tool_name,
                CommercialAgentAction.executed_at >= minute_start,
                CommercialAgentAction.status.in_(["executed", "completed"]),
            )
        )
        day_total = await db.scalar(
            select(func.count(CommercialAgentAction.id)).where(
                CommercialAgentAction.tenant_id == tenant_id,
                CommercialAgentAction.tool_name == tool.tool_name,
                CommercialAgentAction.executed_at >= day_start,
                CommercialAgentAction.status.in_(["executed", "completed"]),
            )
        )

        if minute_total and minute_total >= min(profile.max_actions_per_minute, tool.rate_limit_per_minute):
            return False, "rate_limit_exceeded"
        if day_total and day_total >= min(profile.max_actions_per_day, tool.quota_limit_per_day):
            return False, "quota_exceeded"
        return True, "ok"
