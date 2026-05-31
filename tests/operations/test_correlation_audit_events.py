import pytest
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.operations.correlation.audit_events import (
    log_correlation_created,
    log_trust_link_created,
    log_graph_generated
)
from app.models.admin_action_log import AdminActionLog

@pytest.mark.asyncio
class TestCorrelationAuditEvents:
    
    async def test_log_correlation_created(self, session: AsyncSession):
        client_id = uuid.uuid4()
        correlation_id = uuid.uuid4()
        
        await log_correlation_created(session, client_id, correlation_id, "test_correlation")
        await session.commit()
        
        stmt = select(AdminActionLog).where(AdminActionLog.action == "ops_correlation:operational_correlation_created")
        result = await session.execute(stmt)
        entry = result.scalars().one()
        
        assert entry.payload_json["correlation_id"] == str(correlation_id)
        assert entry.payload_json["client_id"] == str(client_id)
        assert entry.payload_json["advisory_only"] is True
        assert "signature" in entry.payload_json

    async def test_log_trust_link_created(self, session: AsyncSession):
        client_id = uuid.uuid4()
        await log_trust_link_created(session, client_id, "node_a", "node_b")
        await session.commit()
        
        stmt = select(AdminActionLog).where(AdminActionLog.action == "ops_correlation:operational_trust_link_created")
        result = await session.execute(stmt)
        entry = result.scalars().one()
        
        assert entry.payload_json["source_node"] == "node_a"
        assert entry.payload_json["target_node"] == "node_b"

    async def test_log_graph_generated(self, session: AsyncSession):
        client_id = uuid.uuid4()
        summary = {"node_count": 10, "edge_count": 20, "aggregate_confidence": 0.9}
        await log_graph_generated(session, client_id, summary)
        await session.commit()
        
        stmt = select(AdminActionLog).where(AdminActionLog.action == "ops_correlation:trust_graph_generated")
        result = await session.execute(stmt)
        entry = result.scalars().one()
        
        assert entry.payload_json["node_count"] == 10
        assert entry.payload_json["aggregate_confidence"] == 0.9
