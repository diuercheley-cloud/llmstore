from __future__ import annotations

from typing import Any

from app.core.time import utc_now
from app.models.commercial_autonomous_guardrails import (
    CommercialAutonomousExecutionPolicy,
    CommercialAutonomousExecutionReceipt,
    CommercialExecutionBlastRadius,
    CommercialExecutionGuardrailEvent,
    CommercialHumanApprovalCheckpoint,
)
from app.services.routing.commercial_report_export import sanitize_report_payload
from app.services.security.trust_graph import TrustGraphService
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from .autonomous_execution_limits import AutonomousExecutionLimitsService
from .blast_radius_analysis import BlastRadiusAnalysisService, sha256_hex
from .human_checkpointing import HumanCheckpointingService


class AutonomousGuardrailsService:
    def __init__(self) -> None:
        self.blast_radius = BlastRadiusAnalysisService()
        self.checkpointing = HumanCheckpointingService()
        self.limits = AutonomousExecutionLimitsService()
        self.trust_graph = TrustGraphService()

    async def create_policy(
        self,
        db: AsyncSession,
        *,
        policy_name: str,
        action_type: str,
        tenant_id: str | None = None,
        mode: str = "guarded_enforce",
        max_blast_radius_score: float = 0.35,
        require_human_approval: bool = True,
        approval_stages_json: list | None = None,
        runtime_freeze_enabled: bool = False,
        sovereign_hard_stop: bool = True,
        rollback_allowed: bool = False,
        require_signed_model_promotion: bool = True,
        policy_bundle_id=None,
        metadata_json: dict[str, Any] | None = None,
    ) -> CommercialAutonomousExecutionPolicy:
        policy = CommercialAutonomousExecutionPolicy(
            policy_name=policy_name,
            action_type=action_type,
            tenant_id=tenant_id,
            mode=mode,
            max_blast_radius_score=max_blast_radius_score,
            require_human_approval=require_human_approval,
            approval_stages_json=approval_stages_json or [{"stage": 1, "required_approvals": 1}],
            runtime_freeze_enabled=runtime_freeze_enabled,
            sovereign_hard_stop=sovereign_hard_stop,
            rollback_allowed=rollback_allowed,
            require_signed_model_promotion=require_signed_model_promotion,
            policy_bundle_id=policy_bundle_id,
            metadata_json=sanitize_report_payload(metadata_json or {}),
            is_active=True,
        )
        db.add(policy)
        await db.commit()
        await db.refresh(policy)
        return policy

    async def _record_event(
        self,
        db: AsyncSession,
        *,
        event_type: str,
        severity: str,
        request: dict[str, Any],
        decision: str,
        summary: str,
        details_json: dict[str, Any],
    ) -> CommercialExecutionGuardrailEvent:
        sanitized = sanitize_report_payload(request)
        event = CommercialExecutionGuardrailEvent(
            event_type=event_type,
            severity=severity,
            action_type=str(sanitized.get("action_type") or "unknown"),
            target_type=str(sanitized.get("target_type") or "unknown"),
            target_id=sanitized.get("target_id"),
            tenant_id=sanitized.get("tenant_id"),
            decision=decision,
            summary=summary,
            details_json=sanitize_report_payload(details_json),
            immutable_hash=sha256_hex(
                {
                    "decision": decision,
                    "event_type": event_type,
                    "request": sanitized,
                    "summary": summary,
                }
            ),
        )
        db.add(event)
        await db.flush()
        return event

    async def issue_receipt(
        self,
        db: AsyncSession,
        *,
        request: dict[str, Any],
        decision: dict[str, Any],
        blast_radius: CommercialExecutionBlastRadius,
        guardrail_event: CommercialExecutionGuardrailEvent,
    ) -> CommercialAutonomousExecutionReceipt:
        sanitized = sanitize_report_payload(request)
        previous = (
            await db.execute(
                select(CommercialAutonomousExecutionReceipt).order_by(
                    desc(CommercialAutonomousExecutionReceipt.created_at)
                )
            )
        ).scalars().first()
        request_hash = sha256_hex(sanitized)
        approval_hash = decision["approval_chain"].get("approval_hash")
        runtime_hash = None
        runtime_record = decision["runtime_state"].get("record")
        if runtime_record is not None:
            runtime_hash = runtime_record.immutable_hash
        receipt_payload = {
            "action_type": sanitized.get("action_type"),
            "approval_hash": approval_hash,
            "blast_radius_score": blast_radius.blast_radius_score,
            "decision": decision["decision"],
            "event_id": str(guardrail_event.id),
            "previous_receipt_hash": previous.receipt_hash if previous else None,
            "request_hash": request_hash,
            "runtime_hash": runtime_hash,
            "target_id": sanitized.get("target_id"),
            "tenant_id": sanitized.get("tenant_id"),
        }
        receipt_hash = sha256_hex(receipt_payload)
        receipt = CommercialAutonomousExecutionReceipt(
            policy_id=decision["policy"].id if decision.get("policy") else None,
            checkpoint_id=decision["approval_chain"]["checkpoints"][-1].id if decision["approval_chain"].get("checkpoints") else None,
            blast_radius_id=blast_radius.id,
            guardrail_event_id=guardrail_event.id,
            tenant_id=sanitized.get("tenant_id"),
            action_type=str(sanitized.get("action_type") or "unknown"),
            target_type=str(sanitized.get("target_type") or "unknown"),
            target_id=sanitized.get("target_id"),
            execution_mode="guarded",
            decision=decision["decision"],
            request_hash=request_hash,
            approval_hash=approval_hash,
            runtime_hash=runtime_hash,
            receipt_hash=receipt_hash,
            previous_receipt_hash=previous.receipt_hash if previous else None,
            detached_signature=f"autonomous_guardrail_sig_{sha256_hex(receipt_hash)[:48]}",
            immutable_hash=sha256_hex({"receipt_hash": receipt_hash, "timestamp": utc_now().isoformat()}),
            verification_status="pending",
            receipt_json=sanitize_report_payload(
                {
                    **receipt_payload,
                    "reasons": decision["reasons"],
                    "limits_hash": decision["limits_hash"],
                }
            ),
        )
        db.add(receipt)
        await db.flush()
        return receipt

    async def verify_receipt(
        self,
        db: AsyncSession,
        receipt_id,
    ) -> CommercialAutonomousExecutionReceipt:
        receipt = await db.get(CommercialAutonomousExecutionReceipt, receipt_id)
        if receipt is None:
            raise ValueError("receipt_not_found")
        payload = receipt.receipt_json or {}
        expected_hash = sha256_hex(
            {
                "action_type": receipt.action_type,
                "approval_hash": receipt.approval_hash,
                "blast_radius_score": payload.get("blast_radius_score"),
                "decision": receipt.decision,
                "event_id": str(receipt.guardrail_event_id) if receipt.guardrail_event_id else None,
                "previous_receipt_hash": receipt.previous_receipt_hash,
                "request_hash": receipt.request_hash,
                "runtime_hash": receipt.runtime_hash,
                "target_id": receipt.target_id,
                "tenant_id": receipt.tenant_id,
            }
        )
        receipt.verification_status = "verified" if expected_hash == receipt.receipt_hash else "tampered"
        receipt.verified_at = utc_now()
        await db.commit()
        await db.refresh(receipt)
        return receipt

    async def evaluate_request(
        self,
        db: AsyncSession,
        *,
        request: dict[str, Any],
        create_checkpoints_if_missing: bool = True,
    ) -> dict[str, Any]:
        sanitized = sanitize_report_payload(request)
        action_type = str(sanitized.get("action_type") or "unknown")
        policy = await self.limits.resolve_active_policy(db, action_type=action_type, tenant_id=sanitized.get("tenant_id"))
        blast_radius = await self.blast_radius.analyze_and_record(db, request=sanitized, persist=False)
        if create_checkpoints_if_missing and policy and policy.require_human_approval:
            existing = await self.checkpointing.validate_chain(
                db,
                policy_id=policy.id,
                target_type=str(sanitized.get("target_type") or "unknown"),
                target_id=sanitized.get("target_id"),
                tenant_id=sanitized.get("tenant_id"),
            )
            if not existing["checkpoints"]:
                await self.checkpointing.create_checkpoints(db, policy=policy, request=sanitized, persist=False)
        limits = await self.limits.evaluate(db, request=sanitized, blast_radius=blast_radius)
        severity = "critical" if limits["blocked"] else ("high" if limits["pending_approval"] else "low")
        event = await self._record_event(
            db,
            event_type="autonomous_execution_evaluated",
            severity=severity,
            request=sanitized,
            decision=limits["decision"],
            summary="Autonomous guardrails evaluated request",
            details_json={
                "reasons": limits["reasons"],
                "blast_radius_score": blast_radius.blast_radius_score,
                "approval_required": limits["pending_approval"],
            },
        )
        blast_radius.blocked = limits["blocked"] or limits["pending_approval"]
        receipt = await self.issue_receipt(
            db,
            request=sanitized,
            decision=limits,
            blast_radius=blast_radius,
            guardrail_event=event,
        )
        await db.commit()
        await db.refresh(blast_radius)
        await db.refresh(event)
        await db.refresh(receipt)
        await self.integrate_with_trust_graph(db, receipt=receipt)
        return {
            "policy": policy,
            "blast_radius": blast_radius,
            "event": event,
            "receipt": receipt,
            "decision": limits,
        }

    async def execute_guarded_action(
        self,
        db: AsyncSession,
        *,
        request: dict[str, Any],
    ) -> dict[str, Any]:
        evaluation = await self.evaluate_request(db, request=request)
        decision = evaluation["decision"]
        if decision["blocked"]:
            return {
                "status": "blocked",
                "receipt_id": str(evaluation["receipt"].id),
                "reasons": decision["reasons"],
            }
        if decision["pending_approval"]:
            return {
                "status": "pending_approval",
                "receipt_id": str(evaluation["receipt"].id),
                "reasons": decision["reasons"],
            }
        evaluation["receipt"].verification_status = "verified"
        evaluation["receipt"].verified_at = utc_now()
        await db.commit()
        return {
            "status": "executed",
            "receipt_id": str(evaluation["receipt"].id),
            "decision": decision["decision"],
            "reasons": decision["reasons"],
        }

    async def summarize_status(self, db: AsyncSession) -> dict[str, Any]:
        policies = (await db.execute(select(CommercialAutonomousExecutionPolicy))).scalars().all()
        checkpoints = (await db.execute(select(CommercialHumanApprovalCheckpoint))).scalars().all()
        events = (await db.execute(select(CommercialExecutionGuardrailEvent))).scalars().all()
        receipts = (await db.execute(select(CommercialAutonomousExecutionReceipt))).scalars().all()
        blast_rows = (await db.execute(select(CommercialExecutionBlastRadius))).scalars().all()
        freeze_enabled = any(item.runtime_freeze_enabled and item.is_active for item in policies)
        sovereign_hard_stop = any(item.sovereign_hard_stop and item.is_active for item in policies)
        matrix = {
            "low": len([row for row in blast_rows if row.severity == "low"]),
            "medium": len([row for row in blast_rows if row.severity == "medium"]),
            "high": len([row for row in blast_rows if row.severity == "high"]),
            "critical": len([row for row in blast_rows if row.severity == "critical"]),
        }
        heatmap = {
            "blocked": len([row for row in blast_rows if row.blocked]),
            "safe": len([row for row in blast_rows if not row.blocked]),
            "avg_score": round(sum(row.blast_radius_score for row in blast_rows) / len(blast_rows), 4) if blast_rows else 0.0,
        }
        return {
            "policies": {
                "total": len(policies),
                "active": len([item for item in policies if item.is_active]),
            },
            "runtime_freeze_enabled": freeze_enabled,
            "sovereign_hard_stop": sovereign_hard_stop,
            "autonomous_risk_matrix": matrix,
            "blast_radius_heatmap": heatmap,
            "human_approval_queue": {
                "pending": len([item for item in checkpoints if item.status == "pending"]),
                "approved": len([item for item in checkpoints if item.status == "approved"]),
                "rejected": len([item for item in checkpoints if item.status == "rejected"]),
            },
            "violations": len([item for item in events if item.decision == "blocked"]),
            "receipts": {
                "total": len(receipts),
                "verified": len([item for item in receipts if item.verification_status == "verified"]),
            },
        }

    async def integrate_with_trust_graph(
        self,
        db: AsyncSession,
        *,
        receipt: CommercialAutonomousExecutionReceipt,
    ) -> None:
        receipt_node = await self.trust_graph.add_node(
            db,
            "receipt",
            f"autonomous-receipt:{receipt.id}",
            {
                "tenant_id": receipt.tenant_id,
                "action_type": receipt.action_type,
                "decision": receipt.decision,
                "receipt_hash": receipt.receipt_hash,
                "previous_receipt_hash": receipt.previous_receipt_hash,
                "verification_status": receipt.verification_status,
            },
            external_id=f"autonomous-receipt:{receipt.id}",
        )
        if receipt.previous_receipt_hash:
            previous = (
                await db.execute(
                    select(CommercialAutonomousExecutionReceipt).where(
                        CommercialAutonomousExecutionReceipt.receipt_hash == receipt.previous_receipt_hash
                    )
                )
            ).scalar_one_or_none()
            if previous is not None:
                previous_node = await self.trust_graph.add_node(
                    db,
                    "receipt",
                    f"autonomous-receipt:{previous.id}",
                    {
                        "tenant_id": previous.tenant_id,
                        "action_type": previous.action_type,
                        "decision": previous.decision,
                        "receipt_hash": previous.receipt_hash,
                        "previous_receipt_hash": previous.previous_receipt_hash,
                        "verification_status": previous.verification_status,
                    },
                    external_id=f"autonomous-receipt:{previous.id}",
                )
                await self.trust_graph.add_edge(
                    db,
                    previous_node.id,
                    receipt_node.id,
                    "lineage",
                    {"scope": "autonomous_receipt"},
                )
