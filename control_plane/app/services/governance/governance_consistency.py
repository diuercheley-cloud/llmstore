import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.commercial_governance import CommercialPolicyBundle
from app.models.commercial_governance_federation import (
    CommercialGovernanceFederationPeer,
    CommercialFederatedPolicySync,
    CommercialFederatedAuditTrail,
)
from app.services.governance.policy_registry import PolicyRegistryService


class GovernanceConsistencyService:
    def __init__(self):
        self.settings = get_settings()
        self.registry = PolicyRegistryService()

    async def compare_active_policies_across_clusters(
        self,
        db: AsyncSession,
        peer_cluster_id: str,
        bundle_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        peer = await self._get_peer(db, peer_cluster_id)
        if peer.status in ("offline", "disabled"):
            return [{"peer": peer_cluster_id, "error": "Peer is offline or disabled"}]

        stmt = select(CommercialPolicyBundle).where(
            CommercialPolicyBundle.status == "active"
        )
        if bundle_type:
            stmt = stmt.where(CommercialPolicyBundle.bundle_type == bundle_type)
        result = await db.execute(stmt)
        local_active = result.scalars().all()

        comparisons = []
        for local in local_active:
            sync_result = await db.execute(
                select(CommercialFederatedPolicySync).where(
                    and_(
                        CommercialFederatedPolicySync.bundle_name == local.bundle_name,
                        CommercialFederatedPolicySync.source_cluster_id == peer_cluster_id,
                        CommercialFederatedPolicySync.bundle_version == local.bundle_version,
                    )
                ).order_by(CommercialFederatedPolicySync.created_at.desc()).limit(1)
            )
            remote_sync = sync_result.scalar_one_or_none()

            comparison = {
                "bundle_name": local.bundle_name,
                "bundle_version": local.bundle_version,
                "bundle_type": local.bundle_type,
                "local_hash": local.immutable_hash,
                "remote_hash": remote_sync.source_hash if remote_sync else None,
                "consistent": False,
                "notes": [],
            }

            if remote_sync:
                if local.immutable_hash == remote_sync.source_hash:
                    comparison["consistent"] = True
                    comparison["notes"].append("Hashes match across clusters")
                else:
                    comparison["notes"].append(
                        f"Hash mismatch: local={local.immutable_hash[:12]} remote={remote_sync.source_hash[:12]}"
                    )
            else:
                comparison["notes"].append(f"No sync record found for peer {peer_cluster_id}")

            comparisons.append(comparison)

        return comparisons

    async def detect_cross_region_drift(
        self,
        db: AsyncSession,
    ) -> List[Dict[str, Any]]:
        result = await db.execute(select(CommercialGovernanceFederationPeer))
        peers = result.scalars().all()

        drifts = []
        for peer in peers:
            if peer.status in ("offline", "disabled"):
                drifts.append({
                    "peer_cluster_id": peer.peer_cluster_id,
                    "region": peer.region,
                    "status": peer.status,
                    "drift_type": "peer_offline",
                    "severity": "high",
                    "detail": f"Peer {peer.peer_cluster_id} is {peer.status}",
                })
                continue

            syncs_result = await db.execute(
                select(CommercialFederatedPolicySync).where(
                    CommercialFederatedPolicySync.source_cluster_id == peer.peer_cluster_id,
                    CommercialFederatedPolicySync.status == "conflict",
                ).limit(10)
            )
            conflicts = syncs_result.scalars().all()

            for conflict in conflicts:
                drifts.append({
                    "peer_cluster_id": peer.peer_cluster_id,
                    "region": peer.region,
                    "drift_type": "policy_conflict",
                    "severity": "high",
                    "bundle_name": conflict.bundle_name,
                    "bundle_version": conflict.bundle_version,
                    "detail": conflict.conflict_reason or "Unresolved policy conflict",
                })

        return drifts

    async def check_compliance_consistency(
        self,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        result = await db.execute(select(CommercialGovernanceFederationPeer))
        peers = result.scalars().all()

        total_checks = 0
        consistent_count = 0
        drift_count = 0
        offline_count = 0
        issues = []

        for peer in peers:
            if peer.status in ("offline", "disabled"):
                offline_count += 1
                issues.append({
                    "peer": peer.peer_cluster_id,
                    "issue": "peer_offline",
                    "severity": "high",
                    "detail": f"Peer is {peer.status}",
                })
                continue

            comparisons = await self.compare_active_policies_across_clusters(db, peer.peer_cluster_id)
            for comp in comparisons:
                total_checks += 1
                if comp.get("consistent"):
                    consistent_count += 1
                else:
                    drift_count += 1
                    issues.append({
                        "peer": peer.peer_cluster_id,
                        "issue": "policy_inconsistency",
                        "severity": "medium",
                        "bundle_name": comp.get("bundle_name"),
                        "bundle_version": comp.get("bundle_version"),
                        "detail": "; ".join(comp.get("notes", [])),
                    })

        return {
            "total_checks": total_checks,
            "consistent": consistent_count,
            "drift": drift_count,
            "offline_peers": offline_count,
            "issues": issues,
            "overall_status": "consistent" if drift_count == 0 and offline_count == 0 else "inconsistent",
        }

    async def generate_consistency_report(
        self,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        result = await db.execute(select(CommercialGovernanceFederationPeer))
        peers = result.scalars().all()

        consistency = await self.check_compliance_consistency(db)
        cross_region_drift = await self.detect_cross_region_drift(db)

        region_coverage: Dict[str, int] = {}
        for p in peers:
            region_key = p.region or "unknown"
            region_coverage[region_key] = region_coverage.get(region_key, 0) + 1

        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "local_cluster_id": self.settings.commercial_governance_federation_cluster_id,
            "federation_mode": self.settings.commercial_governance_federation_mode,
            "federation_enabled": self.settings.commercial_governance_federation_enabled,
            "peers": [
                {
                    "peer_cluster_id": p.peer_cluster_id,
                    "region": p.region,
                    "environment": p.environment,
                    "status": p.status,
                    "sync_mode": p.sync_mode,
                    "trust_level": p.trust_level,
                }
                for p in peers
            ],
            "region_coverage": region_coverage,
            "compliance_consistency": consistency,
            "cross_region_drifts": cross_region_drift,
            "summary": {
                "total_peers": len(peers),
                "regions_covered": len(region_coverage),
                "overall_status": consistency.get("overall_status", "unknown"),
            },
        }
        return report

    async def _get_peer(self, db: AsyncSession, peer_cluster_id: str) -> CommercialGovernanceFederationPeer:
        result = await db.execute(
            select(CommercialGovernanceFederationPeer)
            .where(CommercialGovernanceFederationPeer.peer_cluster_id == peer_cluster_id)
        )
        peer = result.scalar_one_or_none()
        if not peer:
            raise ValueError(f"Peer {peer_cluster_id} not found")
        return peer
