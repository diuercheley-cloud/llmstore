# Owner: agent-platform
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.models.agents import AgentApprovalRequest
from app.services.agents.approvals.batch_approval import BatchApprovalService
from app.services.agents.approvals.escalation import EscalationService
from app.services.auth import AdminRole
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def mock_db():
    return MagicMock(spec=AsyncSession)

@pytest.mark.asyncio
async def test_auto_escalation_critical_risk(mock_db):
    service = EscalationService(mock_db)
    req_id = uuid.uuid4()
    req = AgentApprovalRequest(id=req_id, risk_level="critical", escalation_status="none", status="pending")
    
    mock_db.execute = AsyncMock(side_effect=[
        MagicMock(scalars=lambda: MagicMock(all=lambda: [req])), # auto_escalate check
        MagicMock(scalar_one_or_none=lambda: req) # individual escalate check
    ])
    
    await service.auto_escalate_high_risk()
    assert req.escalation_status == "escalated"
    assert req.escalated_to_role == "super_admin"

@pytest.mark.asyncio
async def test_batch_approval_logic(mock_db):
    service = BatchApprovalService(mock_db)
    req_ids = [uuid.uuid4(), uuid.uuid4()]
    
    # We need to mock approve_approval_request
    with pytest.MonkeyPatch().context() as m:
        mock_approve = AsyncMock()
        m.setattr("app.services.agents.approvals.batch_approval.approve_approval_request", mock_approve)
        
        results = await service.approve_batch(req_ids, "admin_1", AdminRole.WRITE)
        
        assert len(results) == 2
        assert all(r["status"] == "approved" for r in results)
        assert mock_approve.call_count == 2
