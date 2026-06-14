# Owner: commercial-ops
import uuid
from typing import Any, Dict, Optional

from app.services.runtime_dependencies import get_db_session
from app.models.commercial.commercial_governance import (
    CommercialPolicyArtifact,
    CommercialPolicyBundle,
    CommercialPolicyDriftEvent,
)
from app.services.auth import require_admin
from app.services.governance.policy_engine import PolicyEngineService
from app.services.governance.policy_registry import PolicyRegistryService
from app.services.routing.commercial_report_export import sanitize_report_payload
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(
    prefix="/admin/governance/policies",
    tags=["admin", "governance"],
    dependencies=[Depends(require_admin)],
)

registry_service = PolicyRegistryService()
engine_service = PolicyEngineService()

class PolicyBundlePayload(BaseModel):
    bundle_name: str = Field(min_length=1, max_length=255)
    bundle_version: str = Field(min_length=1, max_length=64)
    bundle_type: str
    rules_json: Dict[str, Any]
    client_id: Optional[uuid.UUID] = None
    metadata_json: Optional[Dict[str, Any]] = None
    mode: str = "dry_run"

class PublishPayload(BaseModel):
    published_by: str = Field(min_length=1, max_length=255)

class ActivatePayload(BaseModel):
    activated_by: str = Field(min_length=1, max_length=255)

class RollbackPayload(BaseModel):
    rolled_back_by: str = Field(min_length=1, max_length=255)

class SimulatePayload(BaseModel):
    runtime_context: Dict[str, Any] = {}

@router.get("")
async def list_policies(
    bundle_type: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    stmt = select(CommercialPolicyBundle).order_by(desc(CommercialPolicyBundle.created_at))
    if bundle_type:
        stmt = stmt.where(CommercialPolicyBundle.bundle_type == bundle_type)
    if status:
        stmt = stmt.where(CommercialPolicyBundle.status == status)
    
    bundles = (await db.execute(stmt)).scalars().all()
    summary = await registry_service.summarize_policy_registry(db)
    
    return {
        "summary": summary,
        "bundles": bundles
    }

@router.post("", status_code=201)
async def create_policy(
    payload: PolicyBundlePayload,
    db: AsyncSession = Depends(get_db_session)
):
    valid, errors = await engine_service.validate_policy_bundle(payload.rules_json)
    if not valid:
        raise HTTPException(status_code=400, detail={"errors": errors})
    
    sanitized = sanitize_report_payload(payload.model_dump())
    bundle = await registry_service.create_policy_bundle(
        db=db,
        **sanitized
    )
    await db.commit()
    await db.refresh(bundle)
    return bundle

@router.post("/{bundle_id}/publish")
async def publish_policy(
    bundle_id: uuid.UUID,
    payload: PublishPayload,
    db: AsyncSession = Depends(get_db_session)
):
    try:
        bundle = await registry_service.publish_policy_bundle(db, bundle_id, payload.published_by)
        
        # Sign the bundle on publish
        bundle.signature = engine_service.sign_policy_bundle(bundle.rules_json, bundle.immutable_hash)
        bundle.signed_by = payload.published_by
        
        await db.commit()
        await db.refresh(bundle)
        return bundle
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{bundle_id}/activate")
async def activate_policy(
    bundle_id: uuid.UUID,
    payload: ActivatePayload,
    db: AsyncSession = Depends(get_db_session)
):
    try:
        bundle = await registry_service.activate_policy_bundle(db, bundle_id, payload.activated_by)
        await db.commit()
        await db.refresh(bundle)
        return bundle
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{bundle_id}/rollback")
async def rollback_policy(
    bundle_id: uuid.UUID,
    payload: RollbackPayload,
    db: AsyncSession = Depends(get_db_session)
):
    try:
        bundle = await registry_service.rollback_policy_bundle(db, bundle_id, payload.rolled_back_by)
        await db.commit()
        await db.refresh(bundle)
        return bundle
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{bundle_id}/simulate")
async def simulate_policy(
    bundle_id: uuid.UUID,
    payload: SimulatePayload,
    db: AsyncSession = Depends(get_db_session)
):
    try:
        results = await engine_service.simulate_policy_bundle(db, bundle_id, payload.runtime_context)
        await db.commit()
        return results
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/drift")
async def get_drift_events(
    resolved: bool = Query(default=False),
    db: AsyncSession = Depends(get_db_session)
):
    stmt = select(CommercialPolicyDriftEvent).where(CommercialPolicyDriftEvent.resolved == resolved).order_by(desc(CommercialPolicyDriftEvent.created_at))
    events = (await db.execute(stmt)).scalars().all()
    return events

@router.post("/drift/detect")
async def detect_drift(
    bundle_type: str,
    client_id: Optional[uuid.UUID] = None,
    runtime_config: Optional[Dict[str, Any]] = None,
    db: AsyncSession = Depends(get_db_session)
):
    events = await engine_service.detect_policy_drift(db, bundle_type, client_id, runtime_config)
    await db.commit()
    return events

@router.get("/artifacts")
async def list_artifacts(
    bundle_id: Optional[uuid.UUID] = None,
    artifact_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    stmt = select(CommercialPolicyArtifact).order_by(desc(CommercialPolicyArtifact.created_at))
    if bundle_id:
        stmt = stmt.where(CommercialPolicyArtifact.bundle_id == bundle_id)
    if artifact_type:
        stmt = stmt.where(CommercialPolicyArtifact.artifact_type == artifact_type)
    
    artifacts = (await db.execute(stmt)).scalars().all()
    return artifacts
