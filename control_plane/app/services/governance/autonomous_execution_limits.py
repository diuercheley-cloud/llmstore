from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.commercial_attestation_runtime import CommercialRuntimeAttestation
from app.models.commercial_autonomous_guardrails import (
    CommercialAutonomousExecutionPolicy,
    CommercialExecutionBlastRadius,
)
from app.models.commercial_confidential_runtime import CommercialConfidentialInferenceSession
from app.models.commercial_governance import CommercialPolicyBundle
from app.models.commercial_model_supply_chain import (
    CommercialModelPromotionBundle,
    CommercialSignedModelRegistryEntry,
)
from app.models.commercial_runtime_fabric import CommercialRuntimeFabricHealth
from app.models.commercial_sovereign_governance import CommercialHardwareAttestationRecord
from app.services.routing.commercial_report_export import sanitize_report_payload

from .blast_radius_analysis import sha256_hex
from .human_checkpointing import HumanCheckpointingService


class AutonomousExecutionLimitsService:
    def __init__(self) -> None:
        self.checkpointing = HumanCheckpointingService()

    async def resolve_active_policy(
        self,
        db: AsyncSession,
        *,
        action_type: str,
        tenant_id: str | None = None,
    ) -> CommercialAutonomousExecutionPolicy | None:
        rows = (
            await db.execute(
                select(CommercialAutonomousExecutionPolicy)
                .where(
                    CommercialAutonomousExecutionPolicy.is_active.is_(True),
                    CommercialAutonomousExecutionPolicy.action_type == action_type,
                )
                .order_by(desc(CommercialAutonomousExecutionPolicy.updated_at))
            )
        ).scalars().all()
        for row in rows:
            if row.tenant_id and tenant_id and row.tenant_id != tenant_id:
                continue
            return row
        return None

    async def _active_bundle(self, db: AsyncSession, policy: CommercialAutonomousExecutionPolicy | None) -> CommercialPolicyBundle | None:
        if policy is None or policy.policy_bundle_id is None:
            return (
                await db.execute(
                    select(CommercialPolicyBundle)
                    .where(CommercialPolicyBundle.status == "active")
                    .order_by(desc(CommercialPolicyBundle.activated_at), desc(CommercialPolicyBundle.created_at))
                )
            ).scalars().first()
        return await db.get(CommercialPolicyBundle, policy.policy_bundle_id)

    async def _runtime_attestation_status(self, db: AsyncSession, request: dict[str, Any]) -> dict[str, Any]:
        stmt = select(CommercialRuntimeAttestation).order_by(desc(CommercialRuntimeAttestation.attested_at))
        cluster_id = request.get("cluster_id")
        node_id = request.get("node_id")
        if cluster_id:
            stmt = stmt.where(CommercialRuntimeAttestation.cluster_id == cluster_id)
        if node_id:
            stmt = stmt.where(CommercialRuntimeAttestation.node_id == node_id)
        record = (await db.execute(stmt)).scalars().first()
        if record is None:
            return {"ok": False, "status": "missing"}
        return {"ok": bool(record.trusted), "status": record.status, "record": record}

    async def _hardware_attestation_status(self, db: AsyncSession, request: dict[str, Any]) -> dict[str, Any]:
        stmt = select(CommercialHardwareAttestationRecord).order_by(desc(CommercialHardwareAttestationRecord.created_at))
        cluster_id = request.get("cluster_id")
        node_id = request.get("node_id")
        if cluster_id:
            stmt = stmt.where(CommercialHardwareAttestationRecord.cluster_id == cluster_id)
        if node_id:
            stmt = stmt.where(CommercialHardwareAttestationRecord.node_id == node_id)
        record = (await db.execute(stmt)).scalars().first()
        if record is None:
            return {"ok": False, "status": "missing"}
        return {"ok": record.status == "trusted", "status": record.status, "record": record}

    async def _quorum_status(self, db: AsyncSession, request: dict[str, Any]) -> dict[str, Any]:
        stmt = select(CommercialRuntimeFabricHealth).order_by(desc(CommercialRuntimeFabricHealth.last_check))
        if request.get("node_id"):
            stmt = stmt.where(CommercialRuntimeFabricHealth.node_id == request["node_id"])
        rows = (await db.execute(stmt)).scalars().all()
        if not rows:
            return {"ok": False, "status": "missing"}
        ok = all(bool(row.quarum_status) for row in rows[:3])
        return {"ok": ok, "status": "healthy" if ok else "degraded"}

    async def _confidential_status(self, db: AsyncSession, request: dict[str, Any]) -> dict[str, Any]:
        if not request.get("confidential_scope"):
            return {"ok": True, "status": "not_required"}
        session_id = request.get("confidential_session_id")
        if not session_id:
            return {"ok": False, "status": "missing_session"}
        session = await db.get(CommercialConfidentialInferenceSession, session_id)
        if session is None:
            return {"ok": False, "status": "missing_session"}
        if session.attestation_status not in {"trusted", "unknown"}:
            return {"ok": False, "status": "attestation_failed"}
        if session.input_mode == "plaintext" and request.get("confidential_runtime_bypass"):
            return {"ok": False, "status": "bypass_blocked"}
        return {"ok": True, "status": session.attestation_status, "session": session}

    async def _model_promotion_status(self, db: AsyncSession, request: dict[str, Any]) -> dict[str, Any]:
        if request.get("action_type") != "model_promotion":
            return {"ok": True, "status": "not_required"}
        bundle_id = request.get("model_promotion_bundle_id")
        registry_entry_id = request.get("registry_entry_id")
        bundle = await db.get(CommercialModelPromotionBundle, bundle_id) if bundle_id else None
        entry = await db.get(CommercialSignedModelRegistryEntry, registry_entry_id) if registry_entry_id else None
        has_signature = bool((bundle and bundle.signature) or (entry and entry.signature))
        return {"ok": has_signature, "status": "signed" if has_signature else "unsigned"}

    def _within_window(self, policy: CommercialAutonomousExecutionPolicy | None, now: datetime | None = None) -> bool:
        if policy is None or not policy.guarded_window_start or not policy.guarded_window_end:
            return True
        now = now or datetime.utcnow()
        current = now.strftime("%H:%M")
        return policy.guarded_window_start <= current <= policy.guarded_window_end

    async def evaluate(
        self,
        db: AsyncSession,
        *,
        request: dict[str, Any],
        blast_radius: CommercialExecutionBlastRadius,
    ) -> dict[str, Any]:
        sanitized = sanitize_report_payload(request)
        action_type = str(sanitized.get("action_type") or "unknown")
        tenant_id = sanitized.get("tenant_id")
        policy = await self.resolve_active_policy(db, action_type=action_type, tenant_id=tenant_id)
        bundle = await self._active_bundle(db, policy)

        runtime_state = await self._runtime_attestation_status(db, sanitized)
        hardware_state = await self._hardware_attestation_status(db, sanitized)
        quorum_state = await self._quorum_status(db, sanitized)
        confidential_state = await self._confidential_status(db, sanitized)
        promotion_state = await self._model_promotion_status(db, sanitized)

        checkpoints = await self.checkpointing.validate_chain(
            db,
            policy_id=policy.id if policy else None,
            target_type=str(sanitized.get("target_type") or "unknown"),
            target_id=sanitized.get("target_id"),
            tenant_id=tenant_id,
        )

        reasons: list[str] = []
        blocked = False
        pending_approval = False

        if bundle is None or bundle.status != "active":
            reasons.append("policy_bundle_inactive")
            blocked = True
        if policy and policy.runtime_freeze_enabled:
            reasons.append("runtime_freeze_mode")
            blocked = True
        if policy and policy.sovereign_hard_stop and sanitized.get("sovereign_scope"):
            reasons.append("sovereign_hard_stop")
            blocked = True
        if not self._within_window(policy):
            reasons.append("outside_guarded_execution_window")
            blocked = True
        if not runtime_state["ok"]:
            reasons.append(f"runtime_trust_state:{runtime_state['status']}")
            blocked = True
        if not hardware_state["ok"]:
            reasons.append(f"hardware_attestation:{hardware_state['status']}")
            blocked = True
        if not quorum_state["ok"]:
            reasons.append(f"quorum_status:{quorum_state['status']}")
            blocked = True
        if not confidential_state["ok"]:
            reasons.append(f"confidential_runtime:{confidential_state['status']}")
            blocked = True
        if not promotion_state["ok"]:
            reasons.append(f"model_promotion:{promotion_state['status']}")
            blocked = True

        affected_tenants = set(sanitized.get("affected_tenants") or [])
        if tenant_id and affected_tenants and affected_tenants != {tenant_id}:
            reasons.append("tenant_isolation_violation")
            blocked = True

        if action_type == "destructive_replay" or sanitized.get("destructive"):
            reasons.append("destructive_replay_blocked")
            blocked = True
        if action_type == "tenant_quarantine" and len(affected_tenants) > 1:
            reasons.append("unrestricted_tenant_quarantine")
            blocked = True
        if action_type == "federation_sync" and not sanitized.get("target_clusters"):
            reasons.append("unrestricted_federation_sync")
            blocked = True
        if sanitized.get("rollback_requested") and not (policy and policy.rollback_allowed):
            reasons.append("unsafe_rollback")
            blocked = True
        if policy and blast_radius.blast_radius_score > policy.max_blast_radius_score:
            reasons.append("blast_radius_exceeds_policy")
            blocked = True
        if policy and policy.require_human_approval and not checkpoints["approved"]:
            reasons.append(checkpoints["reason"] or "approval_required")
            pending_approval = True

        decision = "blocked" if blocked else ("pending_approval" if pending_approval else "allowed")
        return {
            "policy": policy,
            "policy_bundle": bundle,
            "blast_radius": blast_radius,
            "blocked": blocked,
            "pending_approval": pending_approval and not blocked,
            "decision": decision,
            "reasons": reasons,
            "approval_chain": checkpoints,
            "runtime_state": runtime_state,
            "hardware_state": hardware_state,
            "quorum_state": quorum_state,
            "confidential_state": confidential_state,
            "promotion_state": promotion_state,
            "limits_hash": sha256_hex(
                {
                    "action_type": action_type,
                    "blast_radius_score": blast_radius.blast_radius_score,
                    "decision": decision,
                    "reasons": reasons,
                    "tenant_id": tenant_id,
                }
            ),
        }
