# Owner: agent-platform
import logging
import uuid
from typing import Any, Dict

from app.core.config import get_settings
from app.models.agent_federated_memory import FederatedMemorySummary, FederatedSyncEvent
from sqlalchemy.ext.asyncio import AsyncSession

from .sovereignty_policy import SovereigntyPolicy

logger = logging.getLogger(__name__)

class MemorySummarySync:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.policy = SovereigntyPolicy(db)

    async def sync_summary(
        self, 
        peer_id: uuid.UUID, 
        tenant_id: str, 
        summary_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Receives and validates a memory summary from a federated peer.
        """
        if not self.settings.agent_federated_memory_enabled:
            raise PermissionError("Federated memory is disabled.")

        # 1. Policy check
        is_raw = summary_data.get("is_raw", False)
        authorized, reason = await self.policy.validate_sync(peer_id, "summary", is_raw)
        
        if not authorized:
            return {"status": "rejected", "reason": reason}

        # 2. Record summary
        summary = FederatedMemorySummary(
            tenant_id=tenant_id,
            origin_cluster_id=summary_data["origin_cluster_id"],
            summary_text=summary_data["text"],
            keywords=summary_data.get("keywords", []),
            original_memory_id=summary_data["memory_id"]
        )
        self.db.add(summary)
        
        # 3. Log event
        event = FederatedSyncEvent(
            peer_id=peer_id,
            event_type="sync_complete",
            details={"tenant_id": tenant_id, "memory_id": summary_data["memory_id"]}
        )
        self.db.add(event)
        
        await self.db.commit()
        return {"status": "synced", "id": str(summary.id)}
