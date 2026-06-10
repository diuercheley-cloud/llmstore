# Owner: agent-platform
import uuid
from typing import Tuple

from app.models.agents.agent_federated_memory import FederatedMemoryPeer
from sqlalchemy.ext.asyncio import AsyncSession


class SovereigntyPolicy:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def validate_sync(self, peer_id: uuid.UUID, data_type: str, is_raw: bool) -> Tuple[bool, str]:
        """
        Enforces data residency and sovereignty rules for memory synchronization.
        """
        peer = await self.db.get(FederatedMemoryPeer, peer_id)
        if not peer:
            return False, "Peer not registered."

        if not peer.is_active:
            return False, "Peer is inactive."

        # 1. Block raw sync if not explicitly allowed by global and peer policy
        if is_raw:
             # Sovereignty check: Raw data never leaves unless trust is 'sovereign'
             if peer.trust_level != "sovereign":
                  return False, f"Raw data sync forbidden for trust level '{peer.trust_level}'."

        # 2. Data Residency Check
        # Example: US clusters cannot sync certain data types with EU clusters
        prohibited_regions = {
            "sensor_telemetry": ["cn-north-1"],
            "pii_summary": ["us-east-1"] # Simplified example
        }
        
        if data_type in prohibited_regions and peer.data_residency_region in prohibited_regions[data_type]:
             return False, f"Data residency violation: {data_type} cannot reside in {peer.data_residency_region}."

        return True, "Authorized"
