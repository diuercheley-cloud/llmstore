# Owner: agent-platform
import uuid
from typing import Optional

from app.api import deps
from app.services.knowledge_base.document_ingestion import DocumentIngestionService
from app.services.knowledge_base.kb_registry import KBRegistry
from app.services.knowledge_base.kb_reindex import KBReindexService
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

@router.post("/")
async def create_kb(
    name: str,
    description: Optional[str] = None,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_admin_user)
):
    registry = KBRegistry(db)
    kb = await registry.create_kb(current_user.tenant_id, name, description)
    await db.commit()
    return kb

@router.post("/{kb_id}/documents")
async def upload_document(
    kb_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_admin_user)
):
    service = DocumentIngestionService(db)
    content = await file.read()
    job = await service.ingest_file(kb_id, file.filename, content)
    return job

@router.post("/{kb_id}/ingest-url")
async def ingest_url(
    kb_id: uuid.UUID,
    url: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_admin_user)
):
    service = DocumentIngestionService(db)
    try:
        job = await service.ingest_url(kb_id, url)
        return job
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

@router.post("/{kb_id}/reindex")
async def reindex_kb(
    kb_id: uuid.UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_admin_user)
):
    service = KBReindexService(db)
    job = await service.trigger_reindex(kb_id)
    return job

@router.get("/{kb_id}/documents")
async def list_documents(
    kb_id: uuid.UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_admin_user)
):
    from app.models.knowledge_base import KBDocument
    from sqlalchemy import select
    stmt = select(KBDocument).where(KBDocument.kb_id == kb_id)
    res = await db.execute(stmt)
    return list(res.scalars().all())
