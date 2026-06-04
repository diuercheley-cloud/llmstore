import uuid
from typing import Any, Dict, List, Optional

from app.db.session import get_db
from app.services.batches.batch_registry import BatchRegistry
from app.services.batches.batch_result_store import BatchResultStore
from app.services.batches.batch_scheduler import BatchScheduler
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/v1/batches", tags=["Batch API V1"])

# --- Schemas ---

class BatchCreate(BaseModel):
    input_data: List[Dict[str, Any]] # In real API, this would be an input_file_id
    endpoint: str # /v1/chat/completions or /v1/agents/runs
    completion_window: str = "24h"
    metadata: Optional[Dict[str, Any]] = None
    budget_limit: Optional[float] = None

# --- Endpoints ---

@router.post("")
async def create_batch(
    data: BatchCreate,
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    db: AsyncSession = Depends(get_db)
):
    registry = BatchRegistry(db)
    scheduler = BatchScheduler(db)
    
    batch = await registry.create_batch(
        tenant_id=tenant_id,
        input_data=data.input_data,
        budget_limit=data.budget_limit,
        metadata=data.metadata
    )
    
    # Trigger scheduling (in real life, this might be async)
    await scheduler.schedule_batch(batch.id)
    
    await db.commit()
    return {
        "id": str(batch.id),
        "object": "batch",
        "endpoint": data.endpoint,
        "status": batch.status,
        "total_counts": batch.total_items,
        "created_at": int(batch.created_at.timestamp())
    }

@router.get("/{batch_id}")
async def get_batch(
    batch_id: uuid.UUID,
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    db: AsyncSession = Depends(get_db)
):
    registry = BatchRegistry(db)
    batch = await registry.get_batch(tenant_id, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    return {
        "id": str(batch.id),
        "object": "batch",
        "status": batch.status,
        "total_counts": batch.total_items,
        "completed_counts": batch.completed_items,
        "failed_counts": batch.failed_items,
        "created_at": int(batch.created_at.timestamp()),
        "completed_at": int(batch.completed_at.timestamp()) if batch.completed_at else None
    }

@router.get("/{batch_id}/results")
async def get_batch_results(
    batch_id: uuid.UUID,
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    db: AsyncSession = Depends(get_db)
):
    result_store = BatchResultStore(db)
    results = await result_store.get_results(tenant_id, batch_id)
    if not results:
        # Check if batch exists but has no results
        registry = BatchRegistry(db)
        batch = await registry.get_batch(tenant_id, batch_id)
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found")
            
    return {"object": "list", "data": results}

@router.post("/{batch_id}/cancel")
async def cancel_batch(
    batch_id: uuid.UUID,
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    db: AsyncSession = Depends(get_db)
):
    scheduler = BatchScheduler(db)
    success = await scheduler.cancel_batch(tenant_id, batch_id)
    if not success:
        raise HTTPException(status_code=400, detail="Could not cancel batch")
    
    await db.commit()
    return {"id": str(batch_id), "object": "batch", "status": "cancelled"}
