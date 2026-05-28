# Owner: platform-ops
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.dependencies import get_current_admin, get_db
from app.models.operations.adapter_registry import (
    SignedAdapterRegistryEntry,
    AdapterRegistryPolicy,
    AdapterRegistryDecision,
    AdapterRegistryReceipt,
    AdapterRegistryBlocklistEntry,
    AdapterRegistryAllowlistEntry,
)
from app.models.operations.adapter_sandbox import AdapterManifest
from app.services.operations.adapter_registry.registry_service import SignedAdapterRegistryService
from app.services.operations.adapter_registry.policy_engine import AdapterRegistryPolicyEngine
from app.services.operations.adapter_registry.allowlist_blocklist import AdapterRegistryListService
from app.services.operations.adapter_registry.receipts import (
    build_registry_entry_receipt,
    build_registry_decision_receipt,
    build_policy_receipt,
)
from app.services.operations.adapter_registry.hash_utils import sha256_hex, compute_policy_hash

router = APIRouter()

ENGINE = AdapterRegistryPolicyEngine()

# --- Schemas ---

class RegistryEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    adapter_name: str
    adapter_version: str
    adapter_type: str
    manifest_id: uuid.UUID
    manifest_hash: str
    registry_status: str
    registry_hash: str
    signature_placeholder: str
    created_at: datetime

class RegistryEntryRegisterRequest(BaseModel):
    client_id: uuid.UUID
    manifest_id: uuid.UUID

class DecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    decision_type: str
    decision_status: str
    reason: Optional[str]
    decided_by: str
    created_at: datetime

class PolicyCreateRequest(BaseModel):
    client_id: uuid.UUID
    policy_name: str
    allowed_adapter_types: List[str]
    denied_capabilities: List[str]
    require_sandbox: bool = True
    require_dry_run_default: bool = True
    require_approval: bool = True
    allow_offline_only: bool = True

class ListEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    adapter_name: str
    adapter_version: str
    manifest_hash: str
    reason: str
    created_at: datetime

class RegistryEntryRegisterResponse(BaseModel):
    entry: RegistryEntryResponse
    policy_decision: str
    receipt_id: str

# --- Endpoints ---

@router.post("/entries", response_model=RegistryEntryRegisterResponse)
async def register_registry_entry(
    request: RegistryEntryRegisterRequest,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_admin)
):
    # Fetch manifest
    stmt = select(AdapterManifest).where(
        AdapterManifest.id == request.manifest_id,
        AdapterManifest.client_id == request.client_id
    )
    result = await db.execute(stmt)
    manifest = result.scalar_one_or_none()
    if not manifest:
        raise HTTPException(status_code=404, detail="Manifest not found or client mismatch")

    # Check for existing policy
    stmt = select(AdapterRegistryPolicy).where(AdapterRegistryPolicy.client_id == request.client_id)
    result = await db.execute(stmt)
    policy = result.scalar_one_or_none()
    
    if policy:
        compliant, reason = ENGINE.evaluate_manifest(manifest, policy)
        if not compliant:
            raise HTTPException(status_code=400, detail=f"Manifest not compliant with registry policy: {reason}")

    service = SignedAdapterRegistryService(db)
    entry = await service.register_entry(manifest)
    
    receipt = build_registry_entry_receipt(entry)
    db.add(receipt)
    
    await db.commit()
    await db.refresh(entry)
    
    return RegistryEntryRegisterResponse(
        entry=RegistryEntryResponse.from_orm(entry),
        policy_decision="Draft entry created",
        receipt_id=str(receipt.id)
    )

@router.get("/entries", response_model=List[RegistryEntryResponse])
async def list_registry_entries(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_admin)
):
    stmt = select(SignedAdapterRegistryEntry).where(SignedAdapterRegistryEntry.client_id == client_id)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/entries/{entry_id}", response_model=RegistryEntryResponse)
async def get_registry_entry(
    entry_id: uuid.UUID,
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_admin)
):
    stmt = select(SignedAdapterRegistryEntry).where(
        SignedAdapterRegistryEntry.id == entry_id,
        SignedAdapterRegistryEntry.client_id == client_id
    )
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Registry entry not found")
    return entry

@router.post("/entries/{entry_id}/submit", response_model=DecisionResponse)
async def submit_registry_entry(
    entry_id: uuid.UUID,
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_admin)
):
    stmt = select(SignedAdapterRegistryEntry).where(
        SignedAdapterRegistryEntry.id == entry_id,
        SignedAdapterRegistryEntry.client_id == client_id
    )
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Registry entry not found")
    
    service = SignedAdapterRegistryService(db)
    decision = await service.submit_entry(entry, decided_by=admin.email)
    await db.commit()
    return decision

@router.post("/entries/{entry_id}/approve", response_model=DecisionResponse)
async def approve_registry_entry(
    entry_id: uuid.UUID,
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_admin)
):
    stmt = select(SignedAdapterRegistryEntry).where(
        SignedAdapterRegistryEntry.id == entry_id,
        SignedAdapterRegistryEntry.client_id == client_id
    )
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Registry entry not found")
    
    # Check blocklist
    list_service = AdapterRegistryListService(db)
    if await list_service.is_blocked(entry):
        raise HTTPException(status_code=400, detail="Entry is on the blocklist and cannot be approved")
    
    # Fetch manifest and policy for re-evaluation
    stmt = select(AdapterManifest).where(AdapterManifest.id == entry.manifest_id)
    result = await db.execute(stmt)
    manifest = result.scalar_one_or_none()
    
    stmt = select(AdapterRegistryPolicy).where(AdapterRegistryPolicy.client_id == client_id)
    result = await db.execute(stmt)
    policy = result.scalar_one_or_none()
    
    if manifest and policy:
        compliant, reason = ENGINE.evaluate_manifest(manifest, policy)
        if not compliant:
            raise HTTPException(status_code=400, detail=f"Policy violation detected during approval: {reason}")
    elif not manifest:
        raise HTTPException(status_code=404, detail="Underlying manifest not found")
    # If no policy, we assume approval is allowed if admin says so, 
    # but the requirement says "any path that approves registry entry without policy evaluation" should be fixed.
    # So if there is NO policy, should we block? Usually Phase 74 implies a policy MUST exist or defaults apply.
    # The requirement says: "qualquer caminho que aprove registry entry sem policy evaluation"
    # I'll enforce that a policy MUST exist for approval.
    if not policy:
        raise HTTPException(status_code=400, detail="No registry policy found for this client. Policy must be created before approval.")

    service = SignedAdapterRegistryService(db)
    try:
        decision = await service.approve_entry(entry, approved_by=admin.email)
        await db.commit()
        return decision
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/entries/{entry_id}/reject")
async def reject_registry_entry(
    entry_id: uuid.UUID,
    client_id: uuid.UUID,
    reason: str = Query(..., min_length=5),
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_admin)
):
    stmt = select(SignedAdapterRegistryEntry).where(
        SignedAdapterRegistryEntry.id == entry_id,
        SignedAdapterRegistryEntry.client_id == client_id
    )
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Registry entry not found")
    
    service = SignedAdapterRegistryService(db)
    try:
        decision = await service.reject_entry(entry, reason=reason, decided_by=admin.email)
        await db.commit()
        return decision
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/entries/{entry_id}/revoke")
async def revoke_registry_entry(
    entry_id: uuid.UUID,
    client_id: uuid.UUID,
    reason: str = Query(..., min_length=5),
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_admin)
):
    stmt = select(SignedAdapterRegistryEntry).where(
        SignedAdapterRegistryEntry.id == entry_id,
        SignedAdapterRegistryEntry.client_id == client_id
    )
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Registry entry not found")
    
    service = SignedAdapterRegistryService(db)
    try:
        decision = await service.revoke_entry(entry, reason=reason, decided_by=admin.email)
        await db.commit()
        return decision
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/entries/{entry_id}/block")
async def block_registry_entry(
    entry_id: uuid.UUID,
    client_id: uuid.UUID,
    reason: str = Query(..., min_length=5),
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_admin)
):
    stmt = select(SignedAdapterRegistryEntry).where(
        SignedAdapterRegistryEntry.id == entry_id,
        SignedAdapterRegistryEntry.client_id == client_id
    )
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Registry entry not found")
    
    service = SignedAdapterRegistryService(db)
    try:
        decision = await service.block_entry(entry, reason=reason, decided_by=admin.email)
        
        list_service = AdapterRegistryListService(db)
        await list_service.add_to_blocklist(entry, reason=reason)
        
        await db.commit()
        return decision
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/entries/{entry_id}/deprecate")
async def deprecate_registry_entry(
    entry_id: uuid.UUID,
    client_id: uuid.UUID,
    reason: str = Query(..., min_length=5),
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_admin)
):
    stmt = select(SignedAdapterRegistryEntry).where(
        SignedAdapterRegistryEntry.id == entry_id,
        SignedAdapterRegistryEntry.client_id == client_id
    )
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Registry entry not found")
    
    service = SignedAdapterRegistryService(db)
    try:
        decision = await service.deprecate_entry(entry, reason=reason, decided_by=admin.email)
        await db.commit()
        return decision
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/policies")
async def create_registry_policy(
    request: PolicyCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_admin)
):
    payload = request.dict()
    payload.pop("client_id")
    immutable_hash = compute_policy_hash(payload)
    
    policy = AdapterRegistryPolicy(
        client_id=request.client_id,
        policy_name=request.policy_name,
        allowed_adapter_types_json={"allowed_types": request.allowed_adapter_types},
        denied_capabilities_json={"denied": request.denied_capabilities},
        require_sandbox=request.require_sandbox,
        require_dry_run_default=request.require_dry_run_default,
        require_approval=request.require_approval,
        allow_offline_only=request.allow_offline_only,
        immutable_hash=immutable_hash
    )
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return policy

@router.get("/policies")
async def list_registry_policies(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_admin)
):
    stmt = select(AdapterRegistryPolicy).where(AdapterRegistryPolicy.client_id == client_id)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/blocklist", response_model=List[ListEntryResponse])
async def list_blocklist(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_admin)
):
    stmt = select(AdapterRegistryBlocklistEntry).where(AdapterRegistryBlocklistEntry.client_id == client_id)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/allowlist", response_model=List[ListEntryResponse])
async def list_allowlist(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_admin)
):
    stmt = select(AdapterRegistryAllowlistEntry).where(AdapterRegistryAllowlistEntry.client_id == client_id)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/entries/{entry_id}/receipt")
async def generate_entry_receipt(
    entry_id: uuid.UUID,
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_admin)
):
    stmt = select(SignedAdapterRegistryEntry).where(
        SignedAdapterRegistryEntry.id == entry_id,
        SignedAdapterRegistryEntry.client_id == client_id
    )
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Registry entry not found")
    
    receipt = build_registry_entry_receipt(entry)
    db.add(receipt)
    await db.commit()
    await db.refresh(receipt)
    return receipt
