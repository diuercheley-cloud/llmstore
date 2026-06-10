import hashlib
import uuid
from datetime import datetime, UTC
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ...core.config import get_settings
from ...models.commercial.commercial_appliance import (
    CommercialApplianceProfile,
    CommercialOfflineAuditPackage,
    CommercialOfflineModelBundle,
    CommercialOfflineSyncManifest,
)


async def ensure_appliance_profile(db: AsyncSession) -> CommercialApplianceProfile:
    appliance_id = get_settings().commercial_appliance_id
    res = await db.execute(select(CommercialApplianceProfile).where(CommercialApplianceProfile.appliance_id == appliance_id))
    profile = res.scalar_one_or_none()
    
    if not profile:
        profile = CommercialApplianceProfile(
            appliance_id=appliance_id,
            deployment_tier=get_settings().commercial_appliance_deployment_tier,
            is_offline_first=True,
            require_removable_media_auth=get_settings().commercial_appliance_require_removable_media
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
        
    return profile

async def create_offline_sync_manifest(
    db: AsyncSession,
    sync_direction: str,
    payload_type: str,
    media_uuid: Optional[str] = None
) -> CommercialOfflineSyncManifest:
    profile = await ensure_appliance_profile(db)
    
    manifest_hash = hashlib.sha256(f"{profile.appliance_id}-{datetime.now(UTC).timestamp()}".encode()).hexdigest()
    
    manifest = CommercialOfflineSyncManifest(
        appliance_id=profile.appliance_id,
        manifest_hash=manifest_hash,
        sync_direction=sync_direction,
        payload_type=payload_type,
        media_uuid=media_uuid,
        is_verified=False
    )
    db.add(manifest)
    await db.commit()
    await db.refresh(manifest)
    return manifest

async def stage_offline_model_bundle(
    db: AsyncSession,
    model_name: str,
    manifest_id: uuid.UUID
) -> CommercialOfflineModelBundle:
    bundle_hash = hashlib.sha256(model_name.encode()).hexdigest()
    
    bundle = CommercialOfflineModelBundle(
        bundle_hash=bundle_hash,
        model_name=model_name,
        manifest_id=manifest_id,
        promotion_status="staged"
    )
    db.add(bundle)
    await db.commit()
    await db.refresh(bundle)
    return bundle

async def generate_offline_audit_package(
    db: AsyncSession,
    time_window_start: datetime,
    time_window_end: datetime,
    manifest_id: Optional[uuid.UUID] = None
) -> CommercialOfflineAuditPackage:
    package_hash = hashlib.sha256(f"{time_window_start}-{time_window_end}".encode()).hexdigest()
    
    package = CommercialOfflineAuditPackage(
        package_hash=package_hash,
        time_window_start=time_window_start,
        time_window_end=time_window_end,
        manifest_id=manifest_id,
        export_status="generated"
    )
    db.add(package)
    await db.commit()
    await db.refresh(package)
    return package

async def verify_removable_media(
    db: AsyncSession,
    manifest_id: uuid.UUID,
    media_uuid: str
) -> bool:
    profile = await ensure_appliance_profile(db)
    res = await db.execute(select(CommercialOfflineSyncManifest).where(CommercialOfflineSyncManifest.id == manifest_id))
    manifest = res.scalar_one_or_none()
    
    if not manifest:
        return False
        
    if profile.require_removable_media_auth and manifest.media_uuid != media_uuid:
        return False
        
    manifest.is_verified = True
    await db.commit()
    return True

async def summarize_appliance_status(db: AsyncSession) -> dict:
    profile = await ensure_appliance_profile(db)
    
    manifests_count = await db.execute(select(CommercialOfflineSyncManifest))
    bundles_count = await db.execute(select(CommercialOfflineModelBundle))
    packages_count = await db.execute(select(CommercialOfflineAuditPackage))
    
    return {
        "enabled": get_settings().commercial_appliance_mode_enabled,
        "appliance_id": profile.appliance_id,
        "deployment_tier": profile.deployment_tier,
        "is_offline_first": profile.is_offline_first,
        "require_media_auth": profile.require_removable_media_auth,
        "total_manifests": len(manifests_count.scalars().all()),
        "total_bundles": len(bundles_count.scalars().all()),
        "total_audit_packages": len(packages_count.scalars().all())
    }
