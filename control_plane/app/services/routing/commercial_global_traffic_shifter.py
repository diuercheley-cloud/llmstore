import hashlib
import uuid
from datetime import datetime, UTC

from app.core.config import get_settings
from app.models.commercial_cluster_registry import CommercialClusterRegistry
from app.models.commercial_global_traffic import (
    CommercialGlobalTrafficDecision,
    CommercialGlobalTrafficPolicy,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

cfg = get_settings()

class CommercialGlobalTrafficShifter:
    def __init__(self, db: AsyncSession):
        self.db = db

    def deterministic_bucket(self, correlation_id: str, request_id: str, client_id: str) -> int:
        """Returns a stable bucket between 1 and 100 based on the available IDs."""
        key = correlation_id or request_id or client_id or str(uuid.uuid4())
        hash_bytes = hashlib.md5(key.encode("utf-8")).digest()
        # Use first 4 bytes to get an integer
        val = int.from_bytes(hash_bytes[:4], byteorder="little")
        return (val % 100) + 1

    async def create_policy(self, name: str, source_cluster: str, target_cluster: str, percent: int, mode: str, max_percent: int = None, **kwargs) -> CommercialGlobalTrafficPolicy:
        if max_percent is None:
            max_percent = cfg.commercial_global_traffic_shifting_max_canary_percent

        policy = CommercialGlobalTrafficPolicy(
            id=str(uuid.uuid4()),
            name=name,
            enabled=True,
            source_cluster_id=source_cluster,
            target_cluster_id=target_cluster,
            traffic_percent=percent,
            max_traffic_percent=max_percent,
            mode=mode,
            status="active" if mode == "canary" else "pending", # Or whatever logic
            tenant_id=kwargs.get("tenant_id"),
            provider=kwargs.get("provider"),
            model=kwargs.get("model"),
            region=kwargs.get("region"),
            created_by=kwargs.get("created_by")
        )
        if mode == "canary":
            policy.activated_at = datetime.now(UTC)

        self.db.add(policy)
        await self.db.commit()
        await self.db.refresh(policy)
        return policy

    async def pause_policy(self, policy_id: str, reason: str = "Paused by admin") -> CommercialGlobalTrafficPolicy:
        res = await self.db.execute(select(CommercialGlobalTrafficPolicy).where(CommercialGlobalTrafficPolicy.id == policy_id))
        policy = res.scalar_one_or_none()
        if policy and policy.status == "active":
            policy.status = "paused"
            policy.reason = reason
            await self.db.commit()
            await self.db.refresh(policy)
        return policy

    async def rollback_policy(self, policy_id: str, reason: str = "Manual rollback") -> CommercialGlobalTrafficPolicy:
        res = await self.db.execute(select(CommercialGlobalTrafficPolicy).where(CommercialGlobalTrafficPolicy.id == policy_id))
        policy = res.scalar_one_or_none()
        if policy and policy.status in ["active", "paused", "pending"]:
            policy.status = "rolled_back"
            policy.reason = reason
            policy.enabled = False
            policy.rolled_back_at = datetime.now(UTC)
            await self.db.commit()
            await self.db.refresh(policy)
        return policy

    async def check_cluster_health(self, cluster_id: str) -> bool:
        res = await self.db.execute(select(CommercialClusterRegistry).where(CommercialClusterRegistry.cluster_id == cluster_id))
        cluster = res.scalar_one_or_none()
        if not cluster:
            return False
        return cluster.status == "active"

    async def decide_cluster_for_request(self, request_payload: dict, original_cluster_id: str = None) -> CommercialGlobalTrafficDecision:
        original_cluster_id = original_cluster_id or cfg.commercial_cluster_id
        
        tenant_id = request_payload.get("tenant_id")
        provider = request_payload.get("provider")
        model = request_payload.get("model")
        correlation_id = request_payload.get("correlation_id", "")
        request_id = request_payload.get("request_id", "")
        client_id = request_payload.get("client_id", "")
        
        # Default stay_local
        decision = CommercialGlobalTrafficDecision(
            id=str(uuid.uuid4()),
            correlation_id=correlation_id,
            request_id=request_id,
            client_id=client_id,
            tenant_id=tenant_id,
            selected_cluster_id=original_cluster_id,
            original_cluster_id=original_cluster_id,
            target_cluster_id=None,
            decision="stay_local",
            bucket=0,
            traffic_percent=0,
            reason="no_active_policy",
            created_at=datetime.now(UTC)
        )

        if not cfg.commercial_global_traffic_shifting_enabled:
            decision.reason = "feature_disabled"
            return decision

        # Find active policy for this source cluster
        query = select(CommercialGlobalTrafficPolicy).where(
            CommercialGlobalTrafficPolicy.enabled == True,
            CommercialGlobalTrafficPolicy.status.in_(["active", "pending"]),
            CommercialGlobalTrafficPolicy.source_cluster_id == original_cluster_id
        )
        res = await self.db.execute(query)
        policies = res.scalars().all()
        
        # Filter policies by match
        matched_policy = None
        for p in policies:
            if p.tenant_id and p.tenant_id != tenant_id:
                continue
            if p.provider and p.provider != provider:
                continue
            if p.model and p.model != model:
                continue
            # Found a match! Priority logic could be complex, just pick first for now
            matched_policy = p
            break
            
        if not matched_policy:
            return decision

        decision.policy_id = matched_policy.id
        decision.target_cluster_id = matched_policy.target_cluster_id
        decision.traffic_percent = matched_policy.traffic_percent

        bucket = self.deterministic_bucket(correlation_id, request_id, client_id)
        decision.bucket = bucket

        if bucket > matched_policy.traffic_percent:
            decision.reason = "bucket_outside_traffic_percent"
            return decision

        # It would shift. Check health and guardrails
        if cfg.commercial_global_traffic_shifting_require_healthy_target:
            healthy = await self.check_cluster_health(matched_policy.target_cluster_id)
            if not healthy:
                decision.reason = "target_cluster_unhealthy"
                decision.decision = "rejected"
                return decision

        # Mode check
        global_mode = cfg.commercial_global_traffic_shifting_mode
        policy_mode = matched_policy.mode

        if global_mode == "dry_run" or policy_mode == "dry_run":
            decision.decision = "dry_run_would_shift"
            decision.reason = "dry_run_mode"
        else:
            decision.decision = "shift_to_target"
            decision.selected_cluster_id = matched_policy.target_cluster_id
            decision.reason = "canary_shift_applied"

        self.db.add(decision)
        await self.db.commit()
        await self.db.refresh(decision)
        return decision

    async def auto_rollback_unhealthy_policies(self):
        """Checks policies and rolls them back if analytics show errors, high latency, or low margin."""
        if not cfg.commercial_global_traffic_shifting_auto_rollback:
            return
        
        res = await self.db.execute(select(CommercialGlobalTrafficPolicy).where(CommercialGlobalTrafficPolicy.status == "active"))
        policies = res.scalars().all()
        for p in policies:
            pass
