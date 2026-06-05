from typing import Any, Dict, List

from app.db.session import get_db_session
from app.schemas.backup import BackupManifest, BackupSummary
from app.services.backup.backup_service import BackupService
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/admin/backup", tags=["admin-backup"])

# In-memory storage for backup manifests for this prototype
MOCK_BACKUPS: Dict[str, BackupManifest] = {}

@router.post("/create", response_model=BackupManifest)
async def create_backup(db: AsyncSession = Depends(get_db_session)):
    service = BackupService(db)
    manifest = await service.create_backup()
    MOCK_BACKUPS[manifest.backup_id] = manifest
    return manifest

@router.get("/list", response_model=List[BackupSummary])
async def list_backups():
    return [
        BackupSummary(
            id=b.backup_id,
            created_at=b.created_at,
            component_count=len(b.components),
            status="available"
        )
        for b in MOCK_BACKUPS.values()
    ]

@router.get("/{backup_id}/verify")
async def verify_backup(backup_id: str, db: AsyncSession = Depends(get_db_session)):
    if backup_id not in MOCK_BACKUPS:
        raise HTTPException(status_code=404, detail="Backup not found")
    
    service = BackupService(db)
    return service.verify_backup(MOCK_BACKUPS[backup_id])

@router.post("/{backup_id}/restore/dry-run")
async def restore_dry_run(backup_id: str, db: AsyncSession = Depends(get_db_session)):
    if backup_id not in MOCK_BACKUPS:
        raise HTTPException(status_code=404, detail="Backup not found")
    
    service = BackupService(db)
    return await service.restore_dry_run(MOCK_BACKUPS[backup_id])

@router.get("/{backup_id}/status")
async def get_backup_integrity_status(backup_id: str, db: AsyncSession = Depends(get_db_session)):
    if backup_id not in MOCK_BACKUPS:
        raise HTTPException(status_code=404, detail="Backup not found")
        
    service = BackupService(db)
    results = service.verify_backup(MOCK_BACKUPS[backup_id])
    return {"id": backup_id, "integrity": results["status"]}
