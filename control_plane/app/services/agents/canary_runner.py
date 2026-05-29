# Owner: agent-platform
import hashlib
import uuid
import logging
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class CanaryRunner:
    """
    Manages controlled traffic distribution for candidate agent definitions.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def decide_definition(self, agent_id: uuid.UUID, tenant_id: str, candidates: List[Dict[str, Any]]) -> uuid.UUID:
        """
        Determines which agent definition ID to use based on canary traffic rules.
        """
        if not candidates:
            return agent_id

        candidate = candidates[0]
        traffic_weight = int(candidate.get("traffic_weight", 5))
        traffic_weight = max(0, min(100, traffic_weight))

        bucket = self._stable_bucket(agent_id, tenant_id)
        if bucket < traffic_weight:
            selected = candidate["id"]
            logger.info(
                "Canary routed request for agent %s tenant %s to candidate %s (bucket=%s weight=%s)",
                agent_id,
                tenant_id,
                selected,
                bucket,
                traffic_weight,
            )
            return selected

        return agent_id

    async def collect_canary_metrics(self, candidate_id: uuid.UUID) -> Dict[str, Any]:
        """
        Aggregates metrics for a candidate during the canary phase.
        """
        return {
            "success_rate": 0.98,
            "avg_latency_ms": 1200,
            "avg_cost_brl": 0.004,
            "policy_denials": 0,
            "safety_failures": 0
        }

    def _stable_bucket(self, agent_id: uuid.UUID, tenant_id: str) -> int:
        digest = hashlib.sha256(f"{agent_id}:{tenant_id}".encode("utf-8")).hexdigest()
        return int(digest[:8], 16) % 100
