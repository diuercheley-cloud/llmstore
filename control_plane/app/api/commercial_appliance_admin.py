import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from ..db.session import get_db
from ..models.commercial_appliance import (
    CommercialApplianceProfile,
    CommercialOfflineSyncManifest,
    CommercialOfflineModelBundle,
    CommercialOfflineAuditPackage
)
from ..services.inference import sovereign_appliance
from ..api.dependencies import get_admin_user

router = APIRouter(prefix="/admin/inference/appliance", tags=["Sovereign Appliance Admin"])

@router.get("/status")
async def get_status(db: AsyncSession = Depends(get_db), admin: Any = Depends(get_admin_user)):
    return await sovereign_appliance.summarize_appliance_status(db)

@router.get("/manifests", response_model=List[dict])
async def list_manifests(db: AsyncSession = Depends(get_db), admin: Any = Depends(get_admin_user)):
    result = await db.execute(select(CommercialOfflineSyncManifest).order_by(CommercialOfflineSyncManifest.created_at.desc()))
    manifests = result.scalars().all()
    return [
        {
            "id": str(m.id),
            "manifest_hash": m.manifest_hash,
            "sync_direction": m.sync_direction,
            "payload_type": m.payload_type,
            "is_verified": m.is_verified,
            "created_at": m.created_at.isoformat()
        }
        for m in manifests
    ]

@router.post("/manifests")
async def create_manifest(payload: dict, db: AsyncSession = Depends(get_db), admin: Any = Depends(get_admin_user)):
    manifest = await sovereign_appliance.create_offline_sync_manifest(
        db, 
        sync_direction=payload.get("sync_direction", "export"),
        payload_type=payload.get("payload_type", "audits"),
        media_uuid=payload.get("media_uuid")
    )
    return {
        "id": str(manifest.id),
        "manifest_hash": manifest.manifest_hash
    }

@router.get("/bundles", response_model=List[dict])
async def list_bundles(db: AsyncSession = Depends(get_db), admin: Any = Depends(get_admin_user)):
    result = await db.execute(select(CommercialOfflineModelBundle).order_by(CommercialOfflineModelBundle.created_at.desc()).limit(100))
    bundles = result.scalars().all()
    return [
        {
            "id": str(b.id),
            "model_name": b.model_name,
            "bundle_hash": b.bundle_hash,
            "promotion_status": b.promotion_status,
            "created_at": b.created_at.isoformat()
        }
        for b in bundles
    ]

@router.get("/audit-packages", response_model=List[dict])
async def list_audit_packages(db: AsyncSession = Depends(get_db), admin: Any = Depends(get_admin_user)):
    result = await db.execute(select(CommercialOfflineAuditPackage).order_by(CommercialOfflineAuditPackage.created_at.desc()).limit(100))
    packages = result.scalars().all()
    return [
        {
            "id": str(p.id),
            "package_hash": p.package_hash,
            "export_status": p.export_status,
            "time_window_start": p.time_window_start.isoformat(),
            "time_window_end": p.time_window_end.isoformat(),
            "created_at": p.created_at.isoformat()
        }
        for p in packages
    ]

@router.post("/audit-packages")
async def generate_audit_package(payload: dict, db: AsyncSession = Depends(get_db), admin: Any = Depends(get_admin_user)):
    # Default to last 24 hours
    end = datetime.utcnow()
    start = end - timedelta(hours=24)
    
    package = await sovereign_appliance.generate_offline_audit_package(
        db, 
        time_window_start=start,
        time_window_end=end,
        manifest_id=None # Can be linked later
    )
    return {
        "id": str(package.id),
        "package_hash": package.package_hash
    }
