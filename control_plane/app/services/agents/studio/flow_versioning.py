# Owner: agent-platform
import logging
import uuid
from typing import Any, Dict, List, Optional

from app.models.agent_studio import (
    AgentFlowDefinition,
    AgentFlowEdge,
    AgentFlowNode,
    AgentFlowVersion,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

logger = logging.getLogger(__name__)

class FlowVersioningService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_flow(self, tenant_id: str, name: str, description: Optional[str] = None) -> AgentFlowDefinition:
        flow = AgentFlowDefinition(
            tenant_id=tenant_id,
            name=name,
            description=description
        )
        self.db.add(flow)
        await self.db.commit()
        await self.db.refresh(flow)
        return flow

    async def save_version(
        self, 
        flow_id: uuid.UUID, 
        graph_json: Dict[str, Any], 
        version_label: str,
        make_active: bool = False
    ) -> AgentFlowVersion:
        # If make_active, deactivate others
        if make_active:
            stmt = select(AgentFlowVersion).where(AgentFlowVersion.flow_id == flow_id, AgentFlowVersion.is_active == True)
            res = await self.db.execute(stmt)
            active_versions = res.scalars().all()
            for v in active_versions:
                v.is_active = False

        version = AgentFlowVersion(
            flow_id=flow_id,
            version_label=version_label,
            graph_json=graph_json,
            is_active=make_active
        )
        self.db.add(version)
        await self.db.flush()

        # Extract nodes and edges for normalized storage
        await self._sync_normalized_graph(version.id, graph_json)

        # Re-fetch with nodes and edges loaded
        from sqlalchemy.orm import joinedload
        res = await self.db.execute(
            select(AgentFlowVersion)
            .options(joinedload(AgentFlowVersion.nodes), joinedload(AgentFlowVersion.edges))
            .where(AgentFlowVersion.id == version.id)
        )
        return res.unique().scalar_one()

    async def _sync_normalized_graph(self, version_id: uuid.UUID, graph_json: Dict[str, Any]):
        nodes_data = graph_json.get("nodes", [])
        edges_data = graph_json.get("edges", [])

        for nd in nodes_data:
            node = AgentFlowNode(
                id=str(nd.get("id")),
                version_id=version_id,
                node_type=nd.get("node_type"),
                config=nd.get("config", {}),
                position_x=nd.get("position", {}).get("x", 0.0),
                position_y=nd.get("position", {}).get("y", 0.0)
            )
            self.db.add(node)

        for ed in edges_data:
            edge = AgentFlowEdge(
                id=str(ed.get("id")),
                version_id=version_id,
                source_node_id=str(ed.get("source")),
                target_node_id=str(ed.get("target")),
                condition=ed.get("condition")
            )
            self.db.add(edge)

    async def get_active_version(self, flow_id: uuid.UUID) -> Optional[AgentFlowVersion]:
        stmt = select(AgentFlowVersion).where(AgentFlowVersion.flow_id == flow_id, AgentFlowVersion.is_active == True)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_flows(self, tenant_id: str) -> List[AgentFlowDefinition]:
        stmt = select(AgentFlowDefinition).where(AgentFlowDefinition.tenant_id == tenant_id)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
