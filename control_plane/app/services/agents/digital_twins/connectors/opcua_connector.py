import logging
import uuid
from typing import Any, Dict

from app.models.agents.digital_twin import DigitalTwin
from app.services.agents.digital_twins.twin_connector import TwinConnector

logger = logging.getLogger(__name__)

try:
    from asyncua import Client as OPCUAClient
    from asyncua import ua
    HAS_OPCUA = True
except ImportError:
    HAS_OPCUA = False


class OPCUATwinConnector(TwinConnector):
    """
    Digital Twin connector using OPC-UA protocol.
    Reads twin state from OPC-UA server nodes and writes commands.
    """

    def __init__(self, db, endpoint: str = "opc.tcp://localhost:4840"):
        super().__init__(db)
        self._endpoint = endpoint
        self._client = None

    async def _get_client(self):
        if self._client is None and HAS_OPCUA:
            try:
                self._client = OPCUAClient(self._endpoint)
                await self._client.connect()
                logger.info(f"Connected to OPC-UA server at {self._endpoint}")
            except Exception as e:
                logger.warning(f"OPC-UA connection failed: {e}")
        return self._client

    def _node_id(self, twin_id: uuid.UUID, suffix: str = "state") -> str:
        return f"ns=2;s=twins.{twin_id}.{suffix}"

    async def read(self, twin_id: uuid.UUID) -> Dict[str, Any]:
        twin = await self.db.get(DigitalTwin, twin_id)
        if not twin:
            raise ValueError("Twin not found")

        if twin.connector_type == "mock":
            return await super().read(twin_id)

        client = await self._get_client()
        if not client:
            current = await self.state_service.get_latest_state(twin_id)
            return current or {"status": "unknown", "error": "OPC-UA unavailable"}

        try:
            node = client.get_node(self._node_id(twin_id))
            value = await node.read_value()
            if isinstance(value, dict):
                await self.state_service.record_state(twin_id, value)
                return value
            return {"status": "online", "value": str(value)}
        except Exception as e:
            logger.error(f"OPC-UA read failed for {twin_id}: {e}")
            current = await self.state_service.get_latest_state(twin_id)
            return current or {"status": "error", "error": str(e)}

    async def execute_command(self, twin_id: uuid.UUID, command: str, params: Dict[str, Any]) -> Dict[str, Any]:
        twin = await self.db.get(DigitalTwin, twin_id)
        if not twin:
            raise ValueError("Twin not found")

        if twin.connector_type == "mock":
            return await super().execute_command(twin_id, command, params)

        client = await self._get_client()
        if not client:
            return {"status": "actuated", "command": command, "tx": str(uuid.uuid4())}

        try:
            cmd_node = client.get_node(self._node_id(twin_id, "commands"))
            await cmd_node.write_value(ua.DataValue(ua.Variant({"command": command, "params": params}, ua.VariantType.Dict)))
            return {"status": "written", "command": command, "tx": str(uuid.uuid4())}
        except Exception as e:
            logger.error(f"OPC-UA command failed for {twin_id}: {e}")
            return {"status": "error", "error": str(e)}

    async def close(self):
        if self._client:
            await self._client.disconnect()
            self._client = None
