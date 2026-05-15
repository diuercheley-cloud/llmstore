from __future__ import annotations

import logging
import uuid
from datetime import timedelta
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.admin_action_log import AdminActionLog
from app.models.commercial_financial_anomaly import CommercialFinancialAnomaly
from app.models.commercial_revenue_protection_action import CommercialRevenueProtectionAction
from app.models.commercial_revenue_protection_policy import CommercialRevenueProtectionPolicy
from app.services.notifications.revenue_alerts import send_revenue_alert
from app.services.notifications.revenue_escalations import evaluate_escalation_policies
from app.services.routing.commercial_report_export import sanitize_report_payload

logger = logging.getLogger(__name__)

SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}
NON_DESTRUCTIVE_ACTIONS = {
    "notify",
    "safe_mode",
    "restrict_expensive_models",
    "force_local_only",
    "reduce_qos_priority",
    "require_manual_approval",
}
_ACTIVE_CONSTRAINT_ACTIONS: list[dict[str, Any]] = []


def _normalize_mode(mode: str | None) -> str:
    settings = get_settings()
    configured = (settings.commercial_revenue_protection_mode or "report_only").strip()
    if configured == "disabled":
        return "disabled"
    return (mode or configured or "report_only").strip()


def _sanitize_text(value: str | None, limit: int = 1000) -> str | None:
    if value is None:
        return None
    return value.replace("\n", " ").replace("\r", " ")[:limit]


def _scope_matches(policy: CommercialRevenueProtectionPolicy, anomaly: CommercialFinancialAnomaly) -> bool:
    scope_identifier = (policy.scope_identifier or "").strip()
    if policy.scope_type == "global":
        return True
    if policy.scope_type == "client":
        return bool(anomaly.client_id and str(anomaly.client_id) == scope_identifier)
    if policy.scope_type == "provider":
        return bool(anomaly.provider and anomaly.provider == scope_identifier)
    if policy.scope_type == "model":
        return bool(anomaly.model and anomaly.model == scope_identifier)
    if policy.scope_type == "qos_tier":
        metadata = anomaly.metadata_json or {}
        return str(metadata.get("qos_tier") or "") == scope_identifier
    return False


def _build_constraint_delta(
    *,
    policy: CommercialRevenueProtectionPolicy,
    anomaly: CommercialFinancialAnomaly | None,
    action: CommercialRevenueProtectionAction | None = None,
) -> dict[str, Any]:
    scope_identifier = policy.scope_identifier
    target_model = (action.model if action else None) or (anomaly.model if anomaly else None) or scope_identifier
    metadata = sanitize_report_payload(policy.metadata_json or {})
    delta: dict[str, Any] = {
        "_policy_scope_type": policy.scope_type,
        "_policy_scope_identifier": scope_identifier,
        "_policy_name": policy.name,
        "_action_type": policy.action_type,
        "safe_mode": False,
        "force_local_only": False,
        "restricted_models": [],
        "max_cost_override": metadata.get("max_cost_override"),
        "qos_priority_override": None,
        "require_approval": False,
    }
    if policy.action_type == "safe_mode":
        delta["safe_mode"] = True
        delta["force_local_only"] = True
        delta["max_cost_override"] = 0.0 if delta["max_cost_override"] is None else delta["max_cost_override"]
    elif policy.action_type == "restrict_expensive_models":
        if target_model:
            delta["restricted_models"] = [target_model]
    elif policy.action_type == "force_local_only":
        delta["force_local_only"] = True
    elif policy.action_type == "reduce_qos_priority":
        delta["qos_priority_override"] = "reduced"
    elif policy.action_type == "require_manual_approval":
        delta["require_approval"] = True
    return sanitize_report_payload(delta)


def _matches_scope_descriptor(descriptor: dict[str, Any], *, client_id: str | None, provider: str | None, model: str | None, qos_tier: str | None) -> bool:
    scope_type = descriptor.get("_policy_scope_type")
    scope_identifier = descriptor.get("_policy_scope_identifier")
    if scope_type == "global":
        return True
    if scope_type == "client":
        return bool(client_id and scope_identifier == client_id)
    if scope_type == "provider":
        return bool(provider and scope_identifier == provider)
    if scope_type == "model":
        return bool(model and scope_identifier == model)
    if scope_type == "qos_tier":
        return bool(qos_tier and scope_identifier == qos_tier)
    return False


def _merge_constraints(base: dict[str, Any], delta: dict[str, Any]) -> dict[str, Any]:
    restricted = set(base.get("restricted_models") or [])
    restricted.update(delta.get("restricted_models") or [])
    base["restricted_models"] = sorted(restricted)
    base["force_local_only"] = bool(base.get("force_local_only") or delta.get("force_local_only"))
    base["require_approval"] = bool(base.get("require_approval") or delta.get("require_approval"))
    base["safe_mode"] = bool(base.get("safe_mode") or delta.get("safe_mode"))
    if delta.get("qos_priority_override"):
        base["qos_priority_override"] = delta["qos_priority_override"]
    max_cost = delta.get("max_cost_override")
    if max_cost is not None:
        current = base.get("max_cost_override")
        base["max_cost_override"] = max_cost if current is None else min(float(current), float(max_cost))
    return base


async def _audit_event(session: AsyncSession, *, action: str, status: str, payload: dict[str, Any] | None = None, result: dict[str, Any] | None = None) -> None:
    session.add(
        AdminActionLog(
            action=action,
            admin_role="system",
            request_path="/admin/billing/revenue-protection",
            request_method="POST",
            payload_json=sanitize_report_payload(payload or {}),
            result_json=sanitize_report_payload(result or {}),
            status=status,
        )
    )


async def rebuild_revenue_protection_runtime_constraints(session: AsyncSession) -> None:
    global _ACTIVE_CONSTRAINT_ACTIONS
    stmt = (
        select(CommercialRevenueProtectionAction)
        .options(selectinload(CommercialRevenueProtectionAction.policy))
        .where(
            CommercialRevenueProtectionAction.status == "applied",
            CommercialRevenueProtectionAction.reverted_at.is_(None),
        )
        .order_by(CommercialRevenueProtectionAction.created_at.asc())
    )
    result = await session.execute(stmt)
    cache: list[dict[str, Any]] = []
    for action in result.scalars().all():
        policy = action.policy
        if policy is None:
            continue
        cache.append(sanitize_report_payload(action.after_state_json or _build_constraint_delta(policy=policy, anomaly=None, action=action)))
    _ACTIVE_CONSTRAINT_ACTIONS = cache


def get_active_revenue_protection_constraints(
    client_id: str | uuid.UUID | None = None,
    provider: str | None = None,
    model: str | None = None,
    qos_tier: str | None = None,
) -> dict[str, Any]:
    normalized_client_id = str(client_id) if client_id else None
    constraints = {
        "force_local_only": False,
        "restricted_models": [],
        "max_cost_override": None,
        "qos_priority_override": None,
        "require_approval": False,
        "safe_mode": False,
    }
    for descriptor in _ACTIVE_CONSTRAINT_ACTIONS:
        if _matches_scope_descriptor(descriptor, client_id=normalized_client_id, provider=provider, model=model, qos_tier=qos_tier):
            constraints = _merge_constraints(constraints, descriptor)
    return sanitize_report_payload(constraints)


async def enforce_cooldown(
    session: AsyncSession,
    *,
    policy: CommercialRevenueProtectionPolicy,
    anomaly: CommercialFinancialAnomaly | None,
) -> bool:
    cooldown_minutes = policy.cooldown_minutes or get_settings().commercial_revenue_protection_cooldown_minutes
    if cooldown_minutes <= 0:
        return False
    since = utc_now() - timedelta(minutes=cooldown_minutes)
    stmt = select(CommercialRevenueProtectionAction).where(
        CommercialRevenueProtectionAction.policy_id == policy.id,
        CommercialRevenueProtectionAction.created_at >= since,
        CommercialRevenueProtectionAction.reverted_at.is_(None),
    )
    if anomaly is not None:
        if anomaly.client_id is not None:
            stmt = stmt.where(CommercialRevenueProtectionAction.client_id == anomaly.client_id)
        if anomaly.provider:
            stmt = stmt.where(CommercialRevenueProtectionAction.provider == anomaly.provider)
        if anomaly.model:
            stmt = stmt.where(CommercialRevenueProtectionAction.model == anomaly.model)
    result = await session.execute(stmt.limit(1))
    return result.scalar_one_or_none() is not None


def match_anomaly_to_policy(anomaly: CommercialFinancialAnomaly, policy: CommercialRevenueProtectionPolicy) -> bool:
    if not policy.enabled:
        return False
    if anomaly.anomaly_type != policy.trigger_type:
        return False
    if SEVERITY_ORDER.get(anomaly.severity, 0) < SEVERITY_ORDER.get(policy.severity_threshold, 0):
        return False
    return _scope_matches(policy, anomaly)


async def propose_action(
    session: AsyncSession,
    *,
    policy: CommercialRevenueProtectionPolicy,
    anomaly: CommercialFinancialAnomaly | None,
) -> CommercialRevenueProtectionAction:
    effective_mode = _normalize_mode(policy.mode)
    status = "proposed"
    if effective_mode == "approval_required":
        status = "pending_approval"
    elif effective_mode == "enforce":
        status = "proposed"

    reason = _sanitize_text(
        f"Policy '{policy.name}' matched trigger {policy.trigger_type}"
        + (f" for anomaly {anomaly.id}" if anomaly else "")
    )
    action = CommercialRevenueProtectionAction(
        policy_id=policy.id,
        anomaly_id=anomaly.id if anomaly else None,
        client_id=anomaly.client_id if anomaly else None,
        provider=anomaly.provider if anomaly else None,
        model=anomaly.model if anomaly else None,
        action_type=policy.action_type,
        mode=effective_mode,
        status=status,
        reason=reason,
        before_state_json=sanitize_report_payload(
            get_active_revenue_protection_constraints(
                client_id=anomaly.client_id if anomaly else None,
                provider=anomaly.provider if anomaly else None,
                model=anomaly.model if anomaly else None,
                qos_tier=(anomaly.metadata_json or {}).get("qos_tier") if anomaly else None,
            )
        ),
        after_state_json=_build_constraint_delta(policy=policy, anomaly=anomaly),
    )
    session.add(action)
    await _audit_event(
        session,
        action="revenue_protection_proposed",
        status=status,
        payload={"policy_id": str(policy.id), "anomaly_id": str(anomaly.id) if anomaly else None},
        result={"action_type": action.action_type, "mode": action.mode},
    )
    return action


async def apply_action(session: AsyncSession, action: CommercialRevenueProtectionAction) -> CommercialRevenueProtectionAction:
    settings = get_settings()
    policy = action.policy
    if policy is None:
        policy = await session.get(CommercialRevenueProtectionPolicy, action.policy_id)
        action.policy = policy
    if policy is None:
        action.status = "failed"
        await evaluate_escalation_policies(
            session,
            source_type="policy_action",
            source_id=action.id,
            severity="high",
            summary="Revenue protection action failed because the policy could not be loaded.",
            recommendation="Inspect policy persistence and action orchestration.",
            metadata={"action_type": action.action_type},
            trigger_type="failed_revenue_protection_action",
        )
        return action

    if _normalize_mode(action.mode) == "disabled":
        action.status = "blocked"
        await _audit_event(session, action="revenue_protection_apply", status="blocked", payload={"action_id": str(action.id)}, result={"reason": "mode_disabled"})
        await session.commit()
        return action

    if not settings.commercial_revenue_protection_allow_enforce:
        action.status = "blocked"
        await _audit_event(session, action="revenue_protection_apply", status="blocked", payload={"action_id": str(action.id)}, result={"reason": "allow_enforce_false"})
        await session.commit()
        return action

    if action.action_type not in NON_DESTRUCTIVE_ACTIONS:
        action.status = "blocked"
        await _audit_event(session, action="revenue_protection_apply", status="blocked", payload={"action_id": str(action.id)}, result={"reason": "action_not_allowed"})
        await session.commit()
        return action

    if policy.scope_type == "global" and action.action_type not in {"notify", "require_manual_approval", "reduce_qos_priority"}:
        action.status = "blocked"
        await _audit_event(session, action="revenue_protection_apply", status="blocked", payload={"action_id": str(action.id)}, result={"reason": "global_block_not_allowed"})
        await session.commit()
        return action

    action.status = "applied"
    action.applied_at = utc_now()
    await send_revenue_alert(
        {
            "event": "revenue_protection_action_applied",
            "action_id": str(action.id),
            "policy_id": str(action.policy_id),
            "action_type": action.action_type,
            "client_id": str(action.client_id) if action.client_id else None,
            "provider": action.provider,
            "model": action.model,
            "mode": action.mode,
            "reason": action.reason,
        }
    )
    await _audit_event(
        session,
        action="revenue_protection_apply",
        status="applied",
        payload={"action_id": str(action.id), "policy_id": str(action.policy_id)},
        result={"after_state_json": action.after_state_json},
    )
    await session.commit()
    await rebuild_revenue_protection_runtime_constraints(session)
    if action.action_type == "safe_mode" and action.client_id is not None:
        safe_mode_count = (
            await session.execute(
                select(func.count(CommercialRevenueProtectionAction.id)).where(
                    CommercialRevenueProtectionAction.client_id == action.client_id,
                    CommercialRevenueProtectionAction.action_type == "safe_mode",
                    CommercialRevenueProtectionAction.status == "applied",
                    CommercialRevenueProtectionAction.created_at >= utc_now() - timedelta(hours=24),
                )
            )
        ).scalar() or 0
        if safe_mode_count >= 3:
            await evaluate_escalation_policies(
                session,
                source_type="policy_action",
                source_id=action.id,
                severity="high",
                summary=f"Repeated safe_mode activations detected for client {action.client_id}",
                recommendation="Investigate repeated safe_mode activations and revenue protection triggers.",
                metadata={"client_id": str(action.client_id), "safe_mode_count_24h": safe_mode_count},
                trigger_type="repeated_safe_mode_activations",
            )
    return action


async def revert_action(session: AsyncSession, action: CommercialRevenueProtectionAction) -> CommercialRevenueProtectionAction:
    action.reverted_at = utc_now()
    action.status = "reverted"
    await _audit_event(
        session,
        action="revenue_protection_revert",
        status="reverted",
        payload={"action_id": str(action.id)},
        result={"before_state_json": action.before_state_json},
    )
    await session.commit()
    await rebuild_revenue_protection_runtime_constraints(session)
    return action


async def evaluate_revenue_protection_policies(
    session: AsyncSession,
    *,
    anomaly_ids: list[uuid.UUID] | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.commercial_revenue_protection_enabled or settings.commercial_revenue_protection_mode == "disabled":
        return {"enabled": False, "evaluated": 0, "proposed": 0, "applied": 0, "blocked": 0}

    anomalies_stmt = select(CommercialFinancialAnomaly).where(CommercialFinancialAnomaly.status == "open")
    if anomaly_ids:
        anomalies_stmt = anomalies_stmt.where(CommercialFinancialAnomaly.id.in_(anomaly_ids))
    anomalies = (await session.execute(anomalies_stmt.order_by(desc(CommercialFinancialAnomaly.detected_at)))).scalars().all()
    policies = (await session.execute(select(CommercialRevenueProtectionPolicy).where(CommercialRevenueProtectionPolicy.enabled.is_(True)))).scalars().all()

    evaluated = 0
    proposed = 0
    applied = 0
    blocked = 0

    for anomaly in anomalies:
        for policy in policies:
            if not match_anomaly_to_policy(anomaly, policy):
                continue
            evaluated += 1
            if await enforce_cooldown(session, policy=policy, anomaly=anomaly):
                skipped = CommercialRevenueProtectionAction(
                    policy_id=policy.id,
                    anomaly_id=anomaly.id,
                    client_id=anomaly.client_id,
                    provider=anomaly.provider,
                    model=anomaly.model,
                    action_type=policy.action_type,
                    mode=_normalize_mode(policy.mode),
                    status="skipped",
                    reason=_sanitize_text(f"Cooldown active for policy '{policy.name}'"),
                )
                session.add(skipped)
                blocked += 1
                await _audit_event(session, action="revenue_protection_cooldown", status="skipped", payload={"policy_id": str(policy.id), "anomaly_id": str(anomaly.id)}, result={"cooldown_minutes": policy.cooldown_minutes})
                continue

            action = await propose_action(session, policy=policy, anomaly=anomaly)
            proposed += 1
            if action.mode == "enforce":
                await session.flush()
                await apply_action(session, action)
                if action.status == "applied":
                    applied += 1
                elif action.status in {"blocked", "failed"}:
                    blocked += 1

    await session.commit()
    return {
        "enabled": True,
        "mode": settings.commercial_revenue_protection_mode,
        "evaluated": evaluated,
        "proposed": proposed,
        "applied": applied,
        "blocked": blocked,
    }


async def summarize_protection_status(session: AsyncSession) -> dict[str, Any]:
    await rebuild_revenue_protection_runtime_constraints(session)
    policies = (await session.execute(select(CommercialRevenueProtectionPolicy).order_by(CommercialRevenueProtectionPolicy.created_at.desc()))).scalars().all()
    actions = (
        await session.execute(
            select(CommercialRevenueProtectionAction)
            .options(selectinload(CommercialRevenueProtectionAction.policy))
            .order_by(desc(CommercialRevenueProtectionAction.created_at))
            .limit(100)
        )
    ).scalars().all()

    applied = [a for a in actions if a.status == "applied" and a.reverted_at is None]
    safe_mode_clients = sorted({str(a.client_id) for a in applied if a.action_type == "safe_mode" and a.client_id})
    restricted_models: list[str] = []
    for item in applied:
        if item.action_type != "restrict_expensive_models":
            continue
        restricted_models.extend([m for m in (item.after_state_json or {}).get("restricted_models", []) if m])
        if item.model:
            restricted_models.append(item.model)
    restricted_models = sorted(set(restricted_models))
    restricted_models = [item for item in restricted_models if item]
    cooldowns = [a for a in actions if a.status == "skipped" and "Cooldown" in (a.reason or "")]

    return sanitize_report_payload(
        {
            "enabled": get_settings().commercial_revenue_protection_enabled,
            "mode": get_settings().commercial_revenue_protection_mode,
            "allow_enforce": get_settings().commercial_revenue_protection_allow_enforce,
            "policies_active": len([p for p in policies if p.enabled]),
            "actions_proposed": len([a for a in actions if a.status == "proposed"]),
            "actions_pending_approval": len([a for a in actions if a.status == "pending_approval"]),
            "actions_applied": len(applied),
            "clients_in_safe_mode": safe_mode_clients,
            "restricted_models": restricted_models,
            "cooldowns_active": len(cooldowns),
            "constraints_cache": _ACTIVE_CONSTRAINT_ACTIONS,
            "badges": [
                "REPORT_ONLY" if get_settings().commercial_revenue_protection_mode == "report_only" else None,
                "APPROVAL_REQUIRED" if get_settings().commercial_revenue_protection_mode == "approval_required" else None,
                "ENFORCED" if applied else None,
                "COOLDOWN" if cooldowns else None,
                "SAFE_MODE" if safe_mode_clients else None,
            ],
            "recent_actions": [
                {
                    "id": str(a.id),
                    "policy": a.policy.name if a.policy else None,
                    "status": a.status,
                    "action_type": a.action_type,
                    "client_id": str(a.client_id) if a.client_id else None,
                    "provider": a.provider,
                    "model": a.model,
                    "created_at": a.created_at.isoformat(),
                }
                for a in actions[:20]
            ],
        }
    )
