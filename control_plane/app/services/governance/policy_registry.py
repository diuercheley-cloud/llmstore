import hashlib
import json
import uuid
from typing import Any, Dict, Optional

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.commercial.commercial_governance import (
    CommercialPolicyArtifact,
    CommercialPolicyBundle,
)
from app.services.security.tenant_encryption import TenantEncryptionService
from sqlalchemy import and_, desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

_settings = get_settings()
_encryption_service = TenantEncryptionService(_settings)


class PolicyRegistryService:
    @staticmethod
    def calculate_bundle_hash(rules_json: Dict[str, Any], metadata_json: Optional[Dict[str, Any]] = None) -> str:
        content = {
            "rules": rules_json,
            "metadata": metadata_json or {}
        }
        encoded = json.dumps(content, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    async def create_policy_bundle(
        self,
        db: AsyncSession,
        bundle_name: str,
        bundle_version: str,
        bundle_type: str,
        rules_json: Dict[str, Any],
        client_id: Optional[uuid.UUID] = None,
        metadata_json: Optional[Dict[str, Any]] = None,
        mode: str = "dry_run",
    ) -> CommercialPolicyBundle:
        immutable_hash = self.calculate_bundle_hash(rules_json, metadata_json)
        
        bundle = CommercialPolicyBundle(
            bundle_name=bundle_name,
            bundle_version=bundle_version,
            bundle_type=bundle_type,
            rules_json=rules_json,
            client_id=client_id,
            metadata_json=metadata_json,
            mode=mode,
            status="draft",
            immutable_hash=immutable_hash,
        )
        db.add(bundle)
        await db.flush()
        
        # Create initial artifact
        artifact = CommercialPolicyArtifact(
            bundle_id=bundle.id,
            artifact_type="json",
            artifact_hash=immutable_hash,
            artifact_json=rules_json,
        )
        db.add(artifact)
        
        # Phase 36: Encrypted Artifact
        if _settings.commercial_tenant_encryption_enabled:
            await _encryption_service.encrypt_payload(
                db,
                bundle.client_id,
                json.dumps(rules_json),
                artifact_type="policy",
                resource_type="policy_bundle",
                resource_id=str(bundle.id),
                key_purpose="policy",
            )
        
        return bundle

    async def publish_policy_bundle(
        self,
        db: AsyncSession,
        bundle_id: uuid.UUID,
        published_by: str,
    ) -> CommercialPolicyBundle:
        result = await db.execute(select(CommercialPolicyBundle).where(CommercialPolicyBundle.id == bundle_id))
        bundle = result.scalar_one_or_none()
        if not bundle:
            raise ValueError("Policy bundle not found")
        
        if bundle.status != "draft":
            raise ValueError(f"Cannot publish bundle in status {bundle.status}")
        
        bundle.status = "published"
        bundle.published_at = utc_now()
        
        # In a real scenario, we might trigger an approval chain here if required by config
        
        return bundle

    async def activate_policy_bundle(
        self,
        db: AsyncSession,
        bundle_id: uuid.UUID,
        activated_by: str,
    ) -> CommercialPolicyBundle:
        result = await db.execute(select(CommercialPolicyBundle).where(CommercialPolicyBundle.id == bundle_id))
        bundle = result.scalar_one_or_none()
        if not bundle:
            raise ValueError("Policy bundle not found")
        
        if bundle.status not in ["published", "rolled_back"]:
            raise ValueError(f"Cannot activate bundle in status {bundle.status}")
        
        # Deactivate current active bundle of the same type and client
        await db.execute(
            update(CommercialPolicyBundle)
            .where(
                and_(
                    CommercialPolicyBundle.bundle_type == bundle.bundle_type,
                    CommercialPolicyBundle.client_id == bundle.client_id,
                    CommercialPolicyBundle.status == "active",
                    CommercialPolicyBundle.id != bundle.id
                )
            )
            .values(status="deprecated")
        )
        
        bundle.status = "active"
        bundle.activated_at = utc_now()
        
        return bundle

    async def rollback_policy_bundle(
        self,
        db: AsyncSession,
        bundle_id: uuid.UUID,
        rolled_back_by: str,
    ) -> CommercialPolicyBundle:
        result = await db.execute(select(CommercialPolicyBundle).where(CommercialPolicyBundle.id == bundle_id))
        bundle = result.scalar_one_or_none()
        if not bundle:
            raise ValueError("Policy bundle not found")
        
        if bundle.status != "active":
            raise ValueError("Can only rollback an active bundle")
        
        bundle.status = "rolled_back"
        
        # Find previous active bundle to re-activate
        prev_result = await db.execute(
            select(CommercialPolicyBundle)
            .where(
                and_(
                    CommercialPolicyBundle.bundle_type == bundle.bundle_type,
                    CommercialPolicyBundle.client_id == bundle.client_id,
                    CommercialPolicyBundle.status == "deprecated"
                )
            )
            .order_by(desc(CommercialPolicyBundle.activated_at))
            .limit(1)
        )
        prev_bundle = prev_result.scalar_one_or_none()
        if prev_bundle:
            prev_bundle.status = "active"
            prev_bundle.activated_at = utc_now()
        
        return bundle

    async def deprecate_policy_bundle(
        self,
        db: AsyncSession,
        bundle_id: uuid.UUID,
    ) -> CommercialPolicyBundle:
        result = await db.execute(select(CommercialPolicyBundle).where(CommercialPolicyBundle.id == bundle_id))
        bundle = result.scalar_one_or_none()
        if not bundle:
            raise ValueError("Policy bundle not found")
        
        bundle.status = "deprecated"
        return bundle

    async def get_active_policy_bundle(
        self,
        db: AsyncSession,
        bundle_type: str,
        client_id: Optional[uuid.UUID] = None,
    ) -> Optional[CommercialPolicyBundle]:
        result = await db.execute(
            select(CommercialPolicyBundle)
            .where(
                and_(
                    CommercialPolicyBundle.bundle_type == bundle_type,
                    CommercialPolicyBundle.client_id == client_id,
                    CommercialPolicyBundle.status == "active"
                )
            )
        )
        return result.scalar_one_or_none()

    async def summarize_policy_registry(self, db: AsyncSession) -> Dict[str, Any]:
        result = await db.execute(select(CommercialPolicyBundle))
        bundles = result.scalars().all()
        
        summary = {
            "total_bundles": len(bundles),
            "by_status": {},
            "by_type": {},
            "active_bundles": []
        }
        
        for b in bundles:
            summary["by_status"][b.status] = summary["by_status"].get(b.status, 0) + 1
            summary["by_type"][b.bundle_type] = summary["by_type"].get(b.bundle_type, 0) + 1
            if b.status == "active":
                summary["active_bundles"].append({
                    "id": str(b.id),
                    "name": b.bundle_name,
                    "version": b.bundle_version,
                    "type": b.bundle_type,
                    "client_id": str(b.client_id) if b.client_id else None
                })
        
        return summary
