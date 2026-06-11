from __future__ import annotations

from typing import Any
from app.db.session import get_db_session
from app.schemas.backup import (
    BackupCreateRequest,
    BackupManifest,
    BackupRestoreRequest,
    BackupRestoreResult,
    BackupSummary,
    BackupVerificationResult,
    RestoreRequestCreate,
    RestoreRequestResponse,
    RestoreRequestExecute,
)
from app.services.auth import require_admin
from app.services.backup.backup_service import BackupService
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

def _get_actor(admin: Any) -> str:
    if not admin:
        return "system"
    if isinstance(admin, dict):
        return admin.get("role") or admin.get("user", {}).get("username") or "admin"
    if hasattr(admin, "user") and admin.user and hasattr(admin.user, "username"):
        return admin.user.username
    return "admin"

router = APIRouter(
    prefix="/admin/backup",
    tags=["admin-backup"],
    dependencies=[Depends(require_admin)],
)


@router.post("", response_model=BackupManifest)
async def create_backup(
    request: BackupCreateRequest | None = None,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
):
    service = BackupService(db)
    return await service.create_backup(request, actor=_get_actor(admin))


@router.post("/create", response_model=BackupManifest)
async def create_backup_legacy(
    request: BackupCreateRequest | None = None,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
):
    service = BackupService(db)
    return await service.create_backup(request, actor=_get_actor(admin))


@router.get("", response_model=list[BackupSummary])
async def list_backups(db: AsyncSession = Depends(get_db_session)):
    service = BackupService(db)
    return await service.list_backups()


@router.get("/list", response_model=list[BackupSummary])
async def list_backups_legacy(db: AsyncSession = Depends(get_db_session)):
    service = BackupService(db)
    return await service.list_backups()


@router.get("/{backup_id}", response_model=BackupManifest)
async def get_backup(
    backup_id: str,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
):
    service = BackupService(db)
    try:
        return await service.get_backup(backup_id, actor=_get_actor(admin))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{backup_id}/verify", response_model=BackupVerificationResult)
async def verify_backup(
    backup_id: str,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
):
    service = BackupService(db)
    try:
        return await service.verify_backup(backup_id, actor=_get_actor(admin))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{backup_id}/verify", response_model=BackupVerificationResult)
async def verify_backup_post(
    backup_id: str,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
):
    service = BackupService(db)
    try:
        return await service.verify_backup(backup_id, actor=_get_actor(admin))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{backup_id}/restore", response_model=BackupRestoreResult)
async def restore_backup(
    backup_id: str,
    request: BackupRestoreRequest | None = None,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
):
    from app.core.config import get_settings
    settings = get_settings()
    is_dry_run = request is not None and request.dry_run
    if settings.deployment_mode == "production" and not is_dry_run:
        raise HTTPException(
            status_code=400,
            detail="Direct productive restore is disabled in production mode. Please use the strong approval workflow."
        )
    if not settings.backup_restore_enabled and not is_dry_run:
        raise HTTPException(
            status_code=403,
            detail="Restore real está desabilitado por segurança. Use restore em staging ou habilite explicitamente BACKUP_RESTORE_ENABLED."
        )
    from app.services.backup.restore_staging_service import RestoreStagingService
    service = RestoreStagingService(db)
    try:
        return await service.restore_with_staging(backup_id, request, actor=_get_actor(admin))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{backup_id}/restore/dry-run", response_model=BackupRestoreResult)
async def restore_dry_run(
    backup_id: str,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
):
    from app.services.backup.restore_staging_service import RestoreStagingService
    service = RestoreStagingService(db)
    try:
        return await service.restore_with_staging(backup_id, BackupRestoreRequest(dry_run=True), actor=_get_actor(admin))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{backup_id}/status")
async def get_backup_status(
    backup_id: str,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
):
    service = BackupService(db)
    try:
        verification = await service.verify_backup(backup_id, actor=_get_actor(admin))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"id": backup_id, "integrity": verification.status, "verified_at": verification.verified_at}


@router.post("/audit/verify")
async def verify_backup_audit(
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
):
    from app.services.security.immutable_audit import ImmutableAuditStore
    is_valid, failed_block_id, reason = await ImmutableAuditStore.verify_chain(db)
    return {
        "is_valid": is_valid,
        "failed_block_id": failed_block_id,
        "reason": reason
    }


@router.post("/restore-requests", response_model=RestoreRequestResponse)
async def create_restore_request(
    payload: RestoreRequestCreate,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
):
    import uuid
    from datetime import timedelta
    from app.core.time import utc_now
    from app.models.operations.disaster_recovery import RestoreRequest
    
    # Verify backup exists
    service = BackupService(db)
    try:
        manifest = await service.get_backup(payload.backup_id, actor=_get_actor(admin))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    requester = _get_actor(admin)
    expires_at = utc_now() + timedelta(minutes=10)
    
    request_record = RestoreRequest(
        id=uuid.uuid4().hex,
        backup_id=payload.backup_id,
        status="pending",
        requester=requester,
        dry_run=payload.dry_run,
        expires_at=expires_at,
        created_at=utc_now()
    )
    db.add(request_record)
    await db.commit()
    await db.refresh(request_record)
    
    # Audit log: restore_requested
    await service.log_immutable_event(
        action="restore_requested",
        actor=requester,
        backup_id=payload.backup_id,
        key_id=manifest.key_id,
        source=manifest.payload_file,
        target="active_system",
        result="pending",
        checksum=manifest.archive_checksum,
    )
    
    return request_record


@router.post("/restore-requests/{id}/approve", response_model=RestoreRequestResponse)
async def approve_restore_request(
    id: str,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
):
    import uuid
    from sqlalchemy import select
    from app.core.time import utc_now
    from app.core.config import get_settings
    from app.models.operations.disaster_recovery import RestoreRequest
    
    stmt = select(RestoreRequest).where(RestoreRequest.id == id)
    res = await db.execute(stmt)
    request_record = res.scalar_one_or_none()
    
    if not request_record:
        raise HTTPException(status_code=404, detail="Restore request not found")
        
    if request_record.status != "pending":
        raise HTTPException(status_code=400, detail=f"Restore request is in state {request_record.status}, cannot approve.")
        
    # Check expiration
    from datetime import timezone
    expires_at_aware = request_record.expires_at
    if expires_at_aware.tzinfo is None:
        expires_at_aware = expires_at_aware.replace(tzinfo=timezone.utc)
    if expires_at_aware < utc_now():
        request_record.status = "expired"
        await db.commit()
        raise HTTPException(status_code=400, detail="Restore request has expired")
        
    approver = _get_actor(admin)
    settings = get_settings()
    if settings.deployment_mode == "production" and request_record.requester == approver:
        raise HTTPException(status_code=400, detail="Self-approval is blocked in production mode.")
        
    # Approve and generate token
    token = f"token-{uuid.uuid4().hex}"
    request_record.status = "approved"
    request_record.approver = approver
    request_record.token = token
    request_record.approved_at = utc_now()
    
    await db.commit()
    await db.refresh(request_record)
    
    # Audit log: restore_approved
    service = BackupService(db)
    try:
        manifest = await service.get_backup(request_record.backup_id, actor=approver)
        await service.log_immutable_event(
            action="restore_approved",
            actor=approver,
            backup_id=request_record.backup_id,
            key_id=manifest.key_id,
            source=manifest.payload_file,
            target="active_system",
            result="approved",
            checksum=manifest.archive_checksum,
        )
    except Exception:
        pass
        
    return request_record


@router.post("/restore-requests/{id}/execute", response_model=BackupRestoreResult)
async def execute_restore_request(
    id: str,
    payload: RestoreRequestExecute,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
):
    from sqlalchemy import select
    from app.core.time import utc_now
    from app.core.config import get_settings
    from app.models.operations.disaster_recovery import RestoreRequest
    
    stmt = select(RestoreRequest).where(RestoreRequest.id == id)
    res = await db.execute(stmt)
    request_record = res.scalar_one_or_none()
    
    if not request_record:
        raise HTTPException(status_code=404, detail="Restore request not found")
        
    if request_record.status != "approved":
        raise HTTPException(status_code=400, detail="Restore request is not approved")
        
    if request_record.token != payload.token:
        raise HTTPException(status_code=400, detail="Invalid token")
        
    from datetime import timezone
    expires_at_aware = request_record.expires_at
    if expires_at_aware.tzinfo is None:
        expires_at_aware = expires_at_aware.replace(tzinfo=timezone.utc)
    if expires_at_aware < utc_now():
        request_record.status = "expired"
        await db.commit()
        raise HTTPException(status_code=400, detail="Restore request has expired")
        
    # Check BACKUP_RESTORE_ENABLED if not dry_run
    settings = get_settings()
    is_dry_run = request_record.dry_run
    if not settings.backup_restore_enabled and not is_dry_run:
        raise HTTPException(
            status_code=403,
            detail="Restore real está desabilitado por segurança. Use restore em staging ou habilite explicitamente BACKUP_RESTORE_ENABLED."
        )
        
    request_record.status = "executed"
    request_record.executed_at = utc_now()
    await db.commit()
    
    # Trigger restore
    from app.services.backup.restore_staging_service import RestoreStagingService
    service = RestoreStagingService(db)
    
    restore_req = BackupRestoreRequest(dry_run=is_dry_run)
    try:
        return await service.restore_with_staging(request_record.backup_id, restore_req, actor=request_record.requester)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
