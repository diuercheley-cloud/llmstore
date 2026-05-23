# Owner: agent-platform
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.client import Client
from app.models.commercial_federated_workflows import CommercialWorkflowReplayFederationReport
from app.services.auth import require_admin, require_client
from app.services.workflows.federated_consensus import FederatedWorkflowConsensusService
from app.services.workflows.federated_execution import FederatedWorkflowExecutionService
from app.services.workflows.federated_replay import FederatedWorkflowReplayService
from app.services.workflows.workflow_execution_leases import WorkflowExecutionLeaseService

router = APIRouter(tags=["admin", "federated-workflows"])

_execution = FederatedWorkflowExecutionService()
_consensus = FederatedWorkflowConsensusService()
_replay = FederatedWorkflowReplayService()
_leases = WorkflowExecutionLeaseService()


class FederatedExecutionPayload(BaseModel):
    execution_id: uuid.UUID
    region_id: str = Field(min_length=1)
    cluster_id: str = Field(min_length=1)
    federation_mode: str = Field(default="local_only", pattern="^(local_only|push|pull|hybrid|sovereign_airgap)$")
    sovereign_mode: str = Field(default="disabled")
    client_id: str | None = None
    peer_clusters: list[dict[str, str]] | None = None


class FederatedLeasePayload(BaseModel):
    candidates: list[str] = Field(min_length=1)
    ttl_seconds: int = Field(default=60, ge=1)


class FederatedReplayPayload(BaseModel):
    replay_execution_id: uuid.UUID | None = None


def _fed_summary(row) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "workflow_execution_id": str(row.workflow_execution_id),
        "workflow_id": row.workflow_id,
        "tenant_id": row.tenant_id,
        "client_id": row.client_id,
        "region_id": row.region_id,
        "cluster_id": row.cluster_id,
        "execution_hash": row.execution_hash,
        "consensus_status": row.consensus_status,
        "replay_status": row.replay_status,
        "federation_mode": row.federation_mode,
        "sovereign_mode": row.sovereign_mode,
        "lease_owner": row.lease_owner,
        "drift_detected": row.drift_detected,
        "reconciliation_status": row.reconciliation_status,
    }


@router.get("/admin/workflows/federation/overview", dependencies=[Depends(require_admin)])
async def get_federation_overview(
    tenant_id: str | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    return await _execution.overview(db, tenant_id=tenant_id)


@router.get("/admin/workflows/federation/peers", dependencies=[Depends(require_admin)])
async def list_federation_peers(
    tenant_id: str | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    rows = await _execution.list_peers(db, tenant_id=tenant_id)
    return {
        "items": [
            {
                "id": str(row.id),
                "federated_execution_id": str(row.federated_execution_id),
                "peer_cluster_id": row.peer_cluster_id,
                "peer_region_id": row.peer_region_id,
                "trust_status": row.trust_status,
                "consensus_status": row.consensus_status,
                "replay_status": row.replay_status,
            }
            for row in rows
        ]
    }


@router.get("/admin/workflows/federation/executions", dependencies=[Depends(require_admin)])
async def list_federation_executions(
    tenant_id: str | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    rows = await _execution.list_executions(db, tenant_id=tenant_id)
    return {"items": [_fed_summary(row) for row in rows]}


@router.post("/admin/workflows/federation/executions", dependencies=[Depends(require_admin)])
async def create_federation_execution(payload: FederatedExecutionPayload, db: AsyncSession = Depends(get_db_session)):
    row = await _execution.register_execution(
        db,
        execution_id=payload.execution_id,
        region_id=payload.region_id,
        cluster_id=payload.cluster_id,
        federation_mode=payload.federation_mode,
        sovereign_mode=payload.sovereign_mode,
        client_id=payload.client_id,
        peer_clusters=payload.peer_clusters,
    )
    await db.commit()
    await db.refresh(row)
    return _fed_summary(row)


@router.post("/admin/workflows/federation/executions/{federated_execution_id}/lease", dependencies=[Depends(require_admin)])
async def acquire_federation_lease(
    federated_execution_id: uuid.UUID,
    payload: FederatedLeasePayload,
    db: AsyncSession = Depends(get_db_session),
):
    row = await _leases.acquire_lease(
        db,
        federated_execution_id=federated_execution_id,
        candidates=payload.candidates,
        ttl_seconds=payload.ttl_seconds,
    )
    await db.commit()
    return {
        "id": str(row.id),
        "lease_owner": row.lease_owner,
        "lease_token": row.lease_token,
        "status": row.status,
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,
    }


@router.get("/admin/workflows/federation/replay", dependencies=[Depends(require_admin)])
async def list_federation_replays(db: AsyncSession = Depends(get_db_session)):
    rows = (
        await db.execute(
            CommercialWorkflowReplayFederationReport.__table__.select().order_by(
                CommercialWorkflowReplayFederationReport.created_at.desc()
            )
        )
    ).mappings().all()
    return {
        "items": [
            {
                **{k: (str(v) if isinstance(v, uuid.UUID) else v) for k, v in dict(row).items()},
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            }
            for row in rows
        ]
    }


@router.post("/admin/workflows/federation/replay/{federated_execution_id}", dependencies=[Depends(require_admin)])
async def create_federation_replay(
    federated_execution_id: uuid.UUID,
    payload: FederatedReplayPayload,
    db: AsyncSession = Depends(get_db_session),
):
    row = await _replay.validate_replay(
        db,
        federated_execution_id=federated_execution_id,
        replay_execution_id=payload.replay_execution_id,
    )
    await db.commit()
    await db.refresh(row)
    return {
        "id": str(row.id),
        "replay_status": row.replay_status,
        "drift_score": row.drift_score,
        "mismatch_detected": row.mismatch_detected,
        "report_signature": row.report_signature,
    }


@router.get("/admin/workflows/federation/drift", dependencies=[Depends(require_admin)])
async def get_federation_drift(
    tenant_id: str | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    return await _execution.drift_summary(db, tenant_id=tenant_id)


@router.get("/admin/workflows/federation/consensus", dependencies=[Depends(require_admin)])
async def get_federation_consensus(
    federated_execution_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
):
    return await _consensus.validate_consensus(db, federated_execution_id=federated_execution_id)


@router.post("/admin/workflows/federation/consensus/{federated_execution_id}", dependencies=[Depends(require_admin)])
async def reconcile_consensus(
    federated_execution_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
):
    result = await _consensus.reconcile_execution(db, federated_execution_id=federated_execution_id)
    await db.commit()
    return result


@router.post("/admin/workflows/federation/reconcile/{federated_execution_id}", dependencies=[Depends(require_admin)])
async def reconcile_federated_execution(
    federated_execution_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
):
    row = await _execution.reconcile(db, federated_execution_id=federated_execution_id)
    await db.commit()
    await db.refresh(row)
    return _fed_summary(row)


@router.get("/portal/workflows/federation/status")
async def get_portal_federation_status(
    client: Client = Depends(require_client),
    db: AsyncSession = Depends(get_db_session),
):
    rows = await _execution.list_executions(db, tenant_id=str(client.id))
    return {
        "items": [_fed_summary(row) for row in rows],
        "overview": await _execution.overview(db, tenant_id=str(client.id)),
    }
