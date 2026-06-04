# Owner: agent-platform
import logging
import uuid
from typing import Any, Dict

from app.models.digital_twin import DigitalTwin

from .twin_state import TwinState

logger = logging.getLogger(__name__)

class TwinConnector:
    """
    Abstrac base for Digital Twin connectors.
    """
    def __init__(self, db):
        self.db = db
        self.state_service = TwinState(db)

    async def read(self, twin_id: uuid.UUID) -> Dict[str, Any]:
        twin = await self.db.get(DigitalTwin, twin_id)
        if not twin:
            raise ValueError("Twin not found")
            
        if twin.connector_type == "mock":
            # Return current DB state or default mock
            current = await self.state_service.get_latest_state(twin_id)
            return current or {"status": "online", "value": 42, "unit": "unitless"}
            
        raise NotImplementedError(f"Connector {twin.connector_type} not implemented in base.")

    async def execute_command(self, twin_id: uuid.UUID, command: str, params: Dict[str, Any]) -> Dict[str, Any]:
        twin = await self.db.get(DigitalTwin, twin_id)
        if twin.connector_type == "mock":
            logger.info(f"Mock executing {command} on {twin_id}")
            return {"status": "success", "tx": str(uuid.uuid4())}
            
        raise NotImplementedError(f"Connector {twin.connector_type} not implemented in base.")
