from __future__ import annotations

from datetime import timedelta
from typing import Any

from app.core.time import utc_now
from app.models.commercial.commercial_federated_workflows import (
    CommercialFederatedWorkflowExecution,
    CommercialWorkflowExecutionLease,
)
from app.services.workflows.workflow_provenance import sha256_hex
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession


class WorkflowExecutionLeaseService:
    async def _federated_execution(
        self, db: AsyncSession, federated_execution_id
    ) -> CommercialFederatedWorkflowExecution:
        row = await db.get(CommercialFederatedWorkflowExecution, federated_execution_id)
        if row is None:
            raise ValueError("federated_workflow_execution_not_found")
        return row

    async def _leases(
        self, db: AsyncSession, federated_execution_id
    ) -> list[CommercialWorkflowExecutionLease]:
        return (
            (
                await db.execute(
                    select(CommercialWorkflowExecutionLease)
                    .where(
                        CommercialWorkflowExecutionLease.federated_execution_id
                        == federated_execution_id
                    )
                    .order_by(
                        desc(CommercialWorkflowExecutionLease.created_at),
                        desc(CommercialWorkflowExecutionLease.lease_token),
                    )
                )
            )
            .scalars()
            .all()
        )

    async def expire_stale_leases(
        self, db: AsyncSession, *, federated_execution_id
    ) -> list[CommercialWorkflowExecutionLease]:
        now = utc_now()
        expired: list[CommercialWorkflowExecutionLease] = []
        for lease in await self._leases(db, federated_execution_id):
            if lease.status == "active" and lease.expires_at <= now:
                lease.status = "expired"
                expired.append(lease)
        await db.flush()
        return expired

    def deterministic_winner(
        self, *, workflow_id: str, tenant_id: str | None, candidates: list[str]
    ) -> str:
        if not candidates:
            raise ValueError("lease_candidates_required")
        ranked = sorted(
            candidates,
            key=lambda candidate: sha256_hex(
                {
                    "workflow_id": workflow_id,
                    "tenant_id": tenant_id,
                    "candidate": candidate,
                }
            ),
        )
        return ranked[0]

    async def current_owner(
        self, db: AsyncSession, *, federated_execution_id
    ) -> CommercialWorkflowExecutionLease | None:
        await self.expire_stale_leases(db, federated_execution_id=federated_execution_id)
        for lease in await self._leases(db, federated_execution_id):
            if lease.status == "active":
                return lease
        return None

    async def acquire_lease(
        self,
        db: AsyncSession,
        *,
        federated_execution_id,
        candidates: list[str],
        ttl_seconds: int = 60,
        metadata_json: dict[str, Any] | None = None,
    ) -> CommercialWorkflowExecutionLease:
        execution = await self._federated_execution(db, federated_execution_id)
        current = await self.current_owner(db, federated_execution_id=federated_execution_id)
        winner = self.deterministic_winner(
            workflow_id=execution.workflow_id,
            tenant_id=execution.tenant_id,
            candidates=sorted(set(candidates)),
        )
        if current and current.lease_owner == winner:
            current.expires_at = utc_now() + timedelta(seconds=ttl_seconds)
            current.renewed_at = utc_now()
            current.metadata_json = metadata_json or current.metadata_json
            execution.lease_owner = winner
            await db.flush()
            return current
        if current:
            current.status = "superseded"
        previous_hash = current.immutable_hash if current else execution.immutable_hash
        token = (
            max(
                [lease.lease_token for lease in await self._leases(db, federated_execution_id)]
                or [0]
            )
            + 1
        )
        lease = CommercialWorkflowExecutionLease(
            federated_execution_id=execution.id,
            workflow_id=execution.workflow_id,
            tenant_id=execution.tenant_id,
            client_id=execution.client_id,
            region_id=execution.region_id,
            cluster_id=execution.cluster_id,
            execution_hash=execution.execution_hash,
            dag_hash=execution.dag_hash,
            provenance_hash=execution.provenance_hash,
            lease_owner=winner,
            lease_token=token,
            status="active",
            consensus_status=execution.consensus_status,
            replay_status=execution.replay_status,
            federation_mode=execution.federation_mode,
            deterministic_clock=execution.deterministic_clock,
            previous_hash=previous_hash,
            signed_execution_receipt=execution.signed_execution_receipt,
            attestation_summary=execution.attestation_summary,
            sovereign_mode=execution.sovereign_mode,
            expires_at=utc_now() + timedelta(seconds=ttl_seconds),
            renewed_at=utc_now(),
            metadata_json=metadata_json or {},
        )
        lease.immutable_hash = sha256_hex(
            {
                "federated_execution_id": str(execution.id),
                "lease_owner": winner,
                "lease_token": token,
                "previous_hash": previous_hash,
            }
        )
        execution.lease_owner = winner
        db.add(lease)
        await db.flush()
        return lease

    async def renew_lease(
        self,
        db: AsyncSession,
        *,
        federated_execution_id,
        lease_owner: str,
        ttl_seconds: int = 60,
    ) -> CommercialWorkflowExecutionLease:
        lease = await self.current_owner(db, federated_execution_id=federated_execution_id)
        if lease is None or lease.lease_owner != lease_owner:
            raise ValueError("lease_owner_mismatch")
        lease.expires_at = utc_now() + timedelta(seconds=ttl_seconds)
        lease.renewed_at = utc_now()
        await db.flush()
        return lease

    async def failover(
        self,
        db: AsyncSession,
        *,
        federated_execution_id,
        candidates: list[str],
        ttl_seconds: int = 60,
    ) -> CommercialWorkflowExecutionLease:
        leases = await self._leases(db, federated_execution_id)
        last_owner = leases[0].lease_owner if leases else None
        await self.expire_stale_leases(db, federated_execution_id=federated_execution_id)
        current = await self.current_owner(db, federated_execution_id=federated_execution_id)
        excluded_owner = current.lease_owner if current is not None else last_owner
        remaining = [candidate for candidate in candidates if candidate != excluded_owner]
        return await self.acquire_lease(
            db,
            federated_execution_id=federated_execution_id,
            candidates=remaining or candidates,
            ttl_seconds=ttl_seconds,
            metadata_json={"failover": True},
        )
