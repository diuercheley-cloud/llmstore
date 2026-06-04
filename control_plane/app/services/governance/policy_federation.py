import hashlib
import json
import uuid
from typing import Any, Dict, Optional

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.commercial_governance import CommercialPolicyBundle
from app.models.commercial_governance_federation import (
    CommercialFederatedPolicySync,
    CommercialGovernanceFederationPeer,
)
from app.services.governance.policy_engine import PolicyEngineService
from app.services.governance.policy_registry import PolicyRegistryService
from app.services.routing.commercial_report_export import sanitize_report_payload
from app.services.security.offline_crl import is_peer_revoked
from app.services.security.tenant_encryption import TenantEncryptionService
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

_settings = get_settings()
_encryption_service = TenantEncryptionService(_settings)


class PolicyFederationService:
    def __init__(self):
        self.settings = get_settings()
        self.engine = PolicyEngineService()
        self.registry = PolicyRegistryService()

    async def register_governance_peer(
        self,
        db: AsyncSession,
        peer_cluster_id: str,
        environment: str,
        region: Optional[str] = None,
        base_url: Optional[str] = None,
        sync_mode: str = "manual",
        trust_level: str = "trusted",
        status: str = "active",
        metadata_json: Optional[Dict[str, Any]] = None,
    ) -> CommercialGovernanceFederationPeer:
        existing = await db.execute(
            select(CommercialGovernanceFederationPeer)
            .where(CommercialGovernanceFederationPeer.peer_cluster_id == peer_cluster_id)
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Peer {peer_cluster_id} already registered")

        valid_sync_modes = {"pull", "push", "hybrid", "manual"}
        if sync_mode not in valid_sync_modes:
            raise ValueError(f"Invalid sync_mode: {sync_mode}")

        valid_trust = {"trusted", "limited", "readonly"}
        if trust_level not in valid_trust:
            raise ValueError(f"Invalid trust_level: {trust_level}")

        valid_statuses = {"active", "degraded", "offline", "disabled"}
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}")

        sanitized_meta = sanitize_report_payload(metadata_json or {})

        peer = CommercialGovernanceFederationPeer(
            peer_cluster_id=peer_cluster_id,
            region=region,
            environment=environment,
            base_url=base_url,
            status=status,
            sync_mode=sync_mode,
            trust_level=trust_level,
            metadata_json=sanitized_meta,
        )
        db.add(peer)
        await db.flush()
        return peer

    async def export_policy_bundle_for_peer(
        self,
        db: AsyncSession,
        bundle_id: uuid.UUID,
        peer_cluster_id: str,
    ) -> Dict[str, Any]:
        peer = await self._get_peer(db, peer_cluster_id)
        if peer.status == "disabled":
            raise ValueError(f"Peer {peer_cluster_id} is disabled")
        if await is_peer_revoked(db, peer_cluster_id):
            raise ValueError(f"Peer {peer_cluster_id} revoked by offline CRL")

        result = await db.execute(
            select(CommercialPolicyBundle).where(CommercialPolicyBundle.id == bundle_id)
        )
        bundle = result.scalar_one_or_none()
        if not bundle:
            raise ValueError(f"Policy bundle {bundle_id} not found")
        bundle_meta = bundle.metadata_json or {}
        bundle_classification = (
            bundle_meta.get("classification")
            or bundle_meta.get("data_classification")
            or bundle.rules_json.get("classification")
        )
        if bundle_classification == "sovereign_restricted":
            raise ValueError("Sovereign restricted bundles cannot be exported via online federation; use encrypted airgap packages")

        if bundle.client_id:
            allowed_peers = bundle_meta.get("allowed_federation_peers", [])
            if allowed_peers and peer_cluster_id not in allowed_peers:
                raise ValueError(f"Peer {peer_cluster_id} not authorized for tenant-scoped bundle")

        signature = self.engine.sign_policy_bundle(
            bundle.rules_json,
            bundle.immutable_hash,
            self.settings.commercial_governance_federation_shared_token or "governance-federation-secret",
        )
        
        rules_payload = bundle.rules_json
        
        # Phase 36: Confidential Computing & Export Controls
        if _settings.commercial_tenant_encryption_enabled:
            # Block restricted for non-trusted peers
            if peer.trust_level in ("limited", "readonly"):
                rules_payload = await _encryption_service.confidential_export_control(
                    db, bundle.client_id, bundle.rules_json
                )

        export = {
            "bundle_id": str(bundle.id),
            "bundle_name": bundle.bundle_name,
            "bundle_version": bundle.bundle_version,
            "bundle_type": bundle.bundle_type,
            "mode": bundle.mode,
            "status": bundle.status,
            "rules_json": rules_payload,
            "metadata_json": bundle.metadata_json,
            "immutable_hash": bundle.immutable_hash,
            "signed_by": bundle.signed_by,
            "signature": signature,
            "client_id": str(bundle.client_id) if bundle.client_id else None,
            "cluster_id": self.settings.commercial_governance_federation_cluster_id,
        }
        
        # Optional: Encrypt full payload for transit if mode is enforce
        if _settings.commercial_tenant_encryption_mode == "enforce":
            import base64

            from app.services.security.local_aead import AESGCM
            
            transport_key = hashlib.sha256((self.settings.commercial_governance_federation_shared_token or "").encode()).digest()
            aesgcm = AESGCM(transport_key)
            nonce = b"\x00" * 12 
            encoded_payload = json.dumps(export).encode()
            encrypted = aesgcm.encrypt(nonce, encoded_payload, None)
            
            export = {
                "encrypted_bundle": base64.b64encode(encrypted).decode(),
                "payload_hash": hashlib.sha256(encoded_payload).hexdigest(),
                "encryption_mode": "federation_shared_token",
                "source_cluster_id": self.settings.commercial_governance_federation_cluster_id,
            }

        return export

    async def ingest_policy_bundle_from_peer(
        self,
        db: AsyncSession,
        payload: Dict[str, Any],
        peer_token: Optional[str] = None,
        peer_signature: Optional[str] = None,
    ) -> Dict[str, Any]:
        if self.settings.commercial_governance_federation_require_token:
            expected_token = self.settings.commercial_governance_federation_shared_token
            if not expected_token:
                raise ValueError("Federation shared token not configured")
            if not peer_token or peer_token != expected_token:
                raise ValueError("Invalid federation token")

        if self.settings.commercial_governance_federation_require_signature:
            if not peer_signature:
                raise ValueError("Missing bundle signature")
            rules = payload.get("rules_json", {})
            bundle_hash = payload.get("immutable_hash", "")
            expected_sig = self.engine.sign_policy_bundle(
                rules,
                bundle_hash,
                self.settings.commercial_governance_federation_shared_token or "governance-federation-secret",
            )
            if peer_signature != expected_sig:
                raise ValueError("Invalid bundle signature")

        sanitized = sanitize_report_payload(payload)
        bundle_name = sanitized.get("bundle_name", "")
        bundle_version = sanitized.get("bundle_version", "")
        source_hash = sanitized.get("immutable_hash", "")

        conflict_reason = None
        sync_status = "success"

        existing = await db.execute(
            select(CommercialPolicyBundle).where(
                and_(
                    CommercialPolicyBundle.bundle_name == bundle_name,
                    CommercialPolicyBundle.bundle_version == bundle_version,
                    CommercialPolicyBundle.status.in_(["active", "published"]),
                )
            )
        )
        existing_bundle = existing.scalar_one_or_none()
        if existing_bundle and existing_bundle.immutable_hash != source_hash:
            conflict_reason = (
                f"Hash mismatch for {bundle_name} v{bundle_version}: "
                f"local={existing_bundle.immutable_hash[:12]} remote={source_hash[:12]}"
            )
            sync_status = "conflict"

        sync_record = CommercialFederatedPolicySync(
            source_cluster_id=sanitized.get("cluster_id", "unknown"),
            target_cluster_id=self.settings.commercial_governance_federation_cluster_id,
            bundle_id=existing_bundle.id if existing_bundle else None,
            bundle_name=bundle_name,
            bundle_version=bundle_version,
            sync_direction="inbound",
            status=sync_status,
            conflict_reason=conflict_reason,
            source_hash=source_hash,
            target_hash=existing_bundle.immutable_hash if existing_bundle else None,
            records_synced=0,
            completed_at=utc_now(),
        )
        db.add(sync_record)
        await db.flush()

        if sync_status == "conflict":
            return {
                "status": "conflict",
                "conflict_reason": conflict_reason,
                "sync_id": str(sync_record.id),
            }

        if self.settings.commercial_governance_federation_mode == "manual":
            return {
                "status": "received",
                "message": "Policy received. Manual approval required to activate.",
                "bundle_name": bundle_name,
                "bundle_version": bundle_version,
                "sync_id": str(sync_record.id),
            }

        return {
            "status": "success",
            "bundle_name": bundle_name,
            "bundle_version": bundle_version,
            "sync_id": str(sync_record.id),
        }

    async def sync_policy_bundle(
        self,
        db: AsyncSession,
        peer_cluster_id: str,
        bundle_id: uuid.UUID,
        direction: str = "outbound",
    ) -> CommercialFederatedPolicySync:
        peer = await self._get_peer(db, peer_cluster_id)
        if peer.status in ("offline", "disabled"):
            raise ValueError(f"Peer {peer_cluster_id} is not available")

        result = await db.execute(
            select(CommercialPolicyBundle).where(CommercialPolicyBundle.id == bundle_id)
        )
        bundle = result.scalar_one_or_none()
        if not bundle:
            raise ValueError(f"Bundle {bundle_id} not found")

        sync = CommercialFederatedPolicySync(
            source_cluster_id=self.settings.commercial_governance_federation_cluster_id,
            target_cluster_id=peer_cluster_id,
            bundle_id=bundle.id,
            bundle_name=bundle.bundle_name,
            bundle_version=bundle.bundle_version,
            sync_direction=direction,
            status="pending",
            source_hash=bundle.immutable_hash,
            records_synced=0,
        )
        db.add(sync)
        await db.flush()

        peer.last_policy_sync_at = utc_now()
        return sync

    async def detect_policy_conflict(
        self,
        db: AsyncSession,
        bundle_name: str,
        bundle_version: str,
        remote_hash: str,
    ) -> Optional[Dict[str, Any]]:
        result = await db.execute(
            select(CommercialPolicyBundle).where(
                and_(
                    CommercialPolicyBundle.bundle_name == bundle_name,
                    CommercialPolicyBundle.bundle_version == bundle_version,
                )
            )
        )
        local_bundle = result.scalar_one_or_none()

        if not local_bundle:
            return None

        if local_bundle.immutable_hash != remote_hash:
            return {
                "conflict": True,
                "bundle_name": bundle_name,
                "bundle_version": bundle_version,
                "local_hash": local_bundle.immutable_hash,
                "remote_hash": remote_hash,
                "reason": "Hash mismatch: same bundle version has different content",
            }

        return {"conflict": False}

    async def resolve_policy_conflict(
        self,
        db: AsyncSession,
        sync_id: uuid.UUID,
        resolution: str,
    ) -> CommercialFederatedPolicySync:
        result = await db.execute(
            select(CommercialFederatedPolicySync).where(CommercialFederatedPolicySync.id == sync_id)
        )
        sync = result.scalar_one_or_none()
        if not sync:
            raise ValueError(f"Sync record {sync_id} not found")

        if sync.status != "conflict":
            raise ValueError(f"Sync record {sync_id} is not in conflict status")

        if resolution == "accept_remote":
            sync.status = "success"
            sync.conflict_reason = "Resolved: accepted remote version"
        elif resolution == "keep_local":
            sync.status = "skipped"
            sync.conflict_reason = "Resolved: kept local version"
        else:
            raise ValueError(f"Invalid resolution: {resolution}")

        sync.completed_at = utc_now()
        return sync

    async def summarize_federation_status(
        self,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        peers_result = await db.execute(select(CommercialGovernanceFederationPeer))
        peers = peers_result.scalars().all()

        syncs_result = await db.execute(
            select(CommercialFederatedPolicySync).order_by(desc(CommercialFederatedPolicySync.created_at)).limit(100)
        )
        syncs = syncs_result.scalars().all()

        peer_summaries = []
        for p in peers:
            peer_summaries.append({
                "peer_cluster_id": p.peer_cluster_id,
                "region": p.region,
                "environment": p.environment,
                "status": p.status,
                "sync_mode": p.sync_mode,
                "trust_level": p.trust_level,
                "last_policy_sync_at": p.last_policy_sync_at.isoformat() if p.last_policy_sync_at else None,
                "last_audit_sync_at": p.last_audit_sync_at.isoformat() if p.last_audit_sync_at else None,
            })

        sync_summaries = []
        for s in syncs:
            sync_summaries.append({
                "id": str(s.id),
                "source_cluster_id": s.source_cluster_id,
                "target_cluster_id": s.target_cluster_id,
                "bundle_name": s.bundle_name,
                "bundle_version": s.bundle_version,
                "status": s.status,
                "sync_direction": s.sync_direction,
                "created_at": s.created_at.isoformat(),
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
            })

        status_counts = {}
        for s in syncs:
            status_counts[s.status] = status_counts.get(s.status, 0) + 1

        return {
            "peers": peer_summaries,
            "recent_syncs": sync_summaries,
            "sync_summary": status_counts,
            "total_peers": len(peers),
            "online_peers": sum(1 for p in peers if p.status == "active"),
            "offline_peers": sum(1 for p in peers if p.status in ("offline", "disabled")),
            "mode": self.settings.commercial_governance_federation_mode,
            "enabled": self.settings.commercial_governance_federation_enabled,
            "local_cluster_id": self.settings.commercial_governance_federation_cluster_id,
        }

    async def _get_peer(self, db: AsyncSession, peer_cluster_id: str) -> CommercialGovernanceFederationPeer:
        result = await db.execute(
            select(CommercialGovernanceFederationPeer)
            .where(CommercialGovernanceFederationPeer.peer_cluster_id == peer_cluster_id)
        )
        peer = result.scalar_one_or_none()
        if not peer:
            raise ValueError(f"Peer {peer_cluster_id} not found")
        return peer
