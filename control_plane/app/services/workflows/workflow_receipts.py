from __future__ import annotations

from typing import Any

from app.core.time import utc_now
from app.models.commercial_workflows import (
    CommercialWorkflowExecution,
    CommercialWorkflowReceipt,
    CommercialWorkflowStage,
)
from app.services.routing.commercial_report_export import sanitize_report_payload
from app.services.workflows.workflow_provenance import canonical_json, sha256_hex
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession


def _make_signature(receipt_hash: str, algorithm: str = "ed25519") -> str:
    return f"{algorithm}:{sha256_hex({'receipt_hash': receipt_hash, 'scope': 'workflow'})[:48]}"


class WorkflowReceiptService:
    async def issue_execution_receipt(
        self,
        db: AsyncSession,
        execution: CommercialWorkflowExecution,
        *,
        provenance_summary: dict[str, Any],
    ) -> CommercialWorkflowReceipt:
        previous = (
            await db.execute(
                select(CommercialWorkflowReceipt)
                .where(CommercialWorkflowReceipt.tenant_id == execution.tenant_id)
                .order_by(desc(CommercialWorkflowReceipt.created_at))
                .limit(1)
            )
        ).scalar_one_or_none()
        stages = (
            await db.execute(
                select(CommercialWorkflowStage)
                .where(CommercialWorkflowStage.execution_id == execution.id)
                .order_by(CommercialWorkflowStage.stage_order.asc())
            )
        ).scalars().all()
        receipt_body = sanitize_report_payload(
            {
                "execution_id": str(execution.id),
                "tenant_id": execution.tenant_id,
                "definition_id": str(execution.definition_id),
                "status": execution.status,
                "dag_hash": execution.dag_hash,
                "execution_hash_chain": execution.execution_hash_chain,
                "ledger_hash": execution.ledger_hash,
                "provenance_hash": provenance_summary.get("provenance_hash"),
                "stage_hashes": [row.stage_hash for row in stages],
                "checkpoint_hashes": [row.checkpoint_hash for row in stages if row.checkpoint_hash],
                "previous_receipt_hash": previous.receipt_hash if previous else None,
            }
        )
        receipt_hash = sha256_hex(receipt_body)
        receipt = CommercialWorkflowReceipt(
            execution_id=execution.id,
            tenant_id=execution.tenant_id,
            receipt_hash=receipt_hash,
            previous_receipt_hash=previous.receipt_hash if previous else None,
            root_stage_hash=stages[-1].stage_hash if stages else None,
            root_checkpoint_hash=execution.last_checkpoint_hash,
            provenance_hash=provenance_summary.get("provenance_hash"),
            detached_signature=_make_signature(receipt_hash),
            signature_algorithm="ed25519",
            verification_status="pending",
            immutable_hash=sha256_hex(
                {
                    "receipt_hash": receipt_hash,
                    "previous_receipt_hash": previous.receipt_hash if previous else None,
                    "created_at": utc_now().isoformat(),
                }
            ),
            receipt_json=receipt_body,
            export_classification="sanitized",
        )
        db.add(receipt)
        await db.flush()
        return receipt

    async def verify_receipt(
        self,
        db: AsyncSession,
        receipt: CommercialWorkflowReceipt,
    ) -> dict[str, Any]:
        expected_hash = sha256_hex(receipt.receipt_json or {})
        hash_valid = expected_hash == receipt.receipt_hash
        signature_valid = receipt.detached_signature == _make_signature(receipt.receipt_hash)
        previous_valid = True
        if receipt.previous_receipt_hash:
            previous = (
                await db.execute(
                    select(CommercialWorkflowReceipt).where(
                        CommercialWorkflowReceipt.receipt_hash == receipt.previous_receipt_hash
                    )
                )
            ).scalar_one_or_none()
            previous_valid = previous is not None
        receipt.verification_status = "verified" if hash_valid and signature_valid and previous_valid else "tampered"
        receipt.verified_at = utc_now()
        return {
            "receipt_id": str(receipt.id),
            "verification_status": receipt.verification_status,
            "hash_valid": hash_valid,
            "signature_valid": signature_valid,
            "chain_valid": previous_valid,
        }

    async def export_receipt(
        self,
        receipt: CommercialWorkflowReceipt,
        *,
        include_sensitive: bool = False,
    ) -> dict[str, Any]:
        exported = {
            "receipt_id": str(receipt.id),
            "execution_id": str(receipt.execution_id),
            "tenant_id": receipt.tenant_id,
            "receipt_hash": receipt.receipt_hash,
            "previous_receipt_hash": receipt.previous_receipt_hash,
            "root_stage_hash": receipt.root_stage_hash,
            "root_checkpoint_hash": receipt.root_checkpoint_hash,
            "provenance_hash": receipt.provenance_hash,
            "detached_signature": receipt.detached_signature,
            "signature_algorithm": receipt.signature_algorithm,
            "immutable_hash": receipt.immutable_hash,
            "receipt_json": receipt.receipt_json if include_sensitive else sanitize_report_payload(receipt.receipt_json or {}),
            "export_classification": receipt.export_classification,
        }
        exported["export_hash"] = sha256_hex(canonical_json(exported))
        return exported
