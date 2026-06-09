import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.core.config import Settings
from app.models.commercial_infra_simulation import (
    CommercialApprovalRecord,
    CommercialExecutionRecord,
    CommercialInfrastructureSimulation,
)
from app.services.routing.commercial_infra_execution import CommercialInfraExecutionService


@pytest.fixture
def base_settings():
    s = MagicMock(spec=Settings)
    s.commercial_infra_execution_enabled = True
    s.commercial_infra_execution_mode = "execute_opt_in"
    s.commercial_infra_require_approval = True
    s.commercial_infra_require_leader = True
    s.commercial_infra_require_fencing = True
    s.commercial_infra_adapters_enabled = "mock,kubernetes,nomad"
    s.commercial_cluster_id = "test-cluster"
    s.node_id = "test-node"
    s.commercial_k8s_execution_enabled = False
    s.commercial_nomad_execution_enabled = False
    return s

def setup_mock_db(db):
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    db.execute.return_value = mock_result
    db.add = MagicMock()
    return db

@pytest.mark.asyncio
async def test_execution_disabled_blocks(base_settings):
    base_settings.commercial_infra_execution_enabled = False
    
    with patch("app.services.routing.commercial_infra_execution.get_settings", return_value=base_settings):
        svc = CommercialInfraExecutionService()
        db = AsyncMock()
        sim = CommercialInfrastructureSimulation(
            id=uuid.uuid4(),
            simulation_type="scale_up",
            target_scope="cluster",
            target_identifier="test-cluster",
            requested_action_json={"nodes": 1},
            safety_gate_status="allowed"
        )
        db.get.return_value = sim
        
        record = await svc.execute_simulation(db, sim.id, "mock", dry_run=False)
        assert record.status == "blocked"
        assert "disabled" in record.error_message

@pytest.mark.asyncio
async def test_simulation_only_blocks_real(base_settings):
    base_settings.commercial_infra_execution_enabled = True
    base_settings.commercial_infra_execution_mode = "simulation_only"
    
    with patch("app.services.routing.commercial_infra_execution.get_settings", return_value=base_settings):
        svc = CommercialInfraExecutionService()
        db = AsyncMock()
        sim = CommercialInfrastructureSimulation(
            id=uuid.uuid4(),
            simulation_type="scale_up",
            target_scope="cluster",
            target_identifier="test-cluster",
            requested_action_json={"nodes": 1},
            safety_gate_status="allowed"
        )
        db.get.return_value = sim
        
        record = await svc.execute_simulation(db, sim.id, "mock", dry_run=False)
        assert record.status == "blocked"
        assert "simulation_only" in record.error_message

@pytest.mark.asyncio
async def test_dry_run_allowed_without_approval(base_settings):
    base_settings.commercial_infra_execution_enabled = True
    base_settings.commercial_infra_execution_mode = "execute_opt_in"
    base_settings.commercial_infra_require_approval = True
    
    with patch("app.services.routing.commercial_infra_execution.get_settings", return_value=base_settings):
        svc = CommercialInfraExecutionService()
        db = AsyncMock()
        setup_mock_db(db)
        sim = CommercialInfrastructureSimulation(
            id=uuid.uuid4(),
            simulation_type="scale_up",
            target_scope="cluster",
            target_identifier="test-cluster",
            requested_action_json={"nodes": 1},
            safety_gate_status="allowed"
        )
        db.get.return_value = sim
        
        record = await svc.execute_simulation(db, sim.id, "mock", dry_run=True)
        assert record.status == "dry_run"
        assert record.dry_run is True

@pytest.mark.asyncio
async def test_real_execution_requires_approval_and_leader(base_settings):
    base_settings.commercial_infra_execution_enabled = True
    base_settings.commercial_infra_execution_mode = "execute_opt_in"
    base_settings.commercial_infra_require_approval = True
    base_settings.commercial_infra_require_leader = True
    
    with patch("app.services.routing.commercial_infra_execution.get_settings", return_value=base_settings):
        svc = CommercialInfraExecutionService()
        db = AsyncMock()
        setup_mock_db(db)
        sim = CommercialInfrastructureSimulation(
            id=uuid.uuid4(),
            simulation_type="scale_up",
            target_scope="cluster",
            target_identifier="test-cluster",
            requested_action_json={"nodes": 1},
            safety_gate_status="allowed"
        )
        db.get.return_value = sim
        
        # 1. Test without approval
        record = await svc.execute_simulation(db, sim.id, "mock", dry_run=False, confirm=True)
        assert record.status == "blocked"
        assert "approved" in record.error_message
        
        # 2. Add approval (mock)
        approval = CommercialApprovalRecord(
            id=uuid.uuid4(),
            simulation_id=sim.id,
            status="approved"
        )
        db.execute.return_value.scalars.return_value.first.return_value = approval
        
        # 3. Test without leader
        with patch("app.services.routing.commercial_infra_execution.is_current_leader", new_callable=AsyncMock) as mock_is_leader:
            mock_is_leader.return_value = False
            
            record = await svc.execute_simulation(db, sim.id, "mock", dry_run=False, confirm=True, approval_id=approval.id)
            assert record.status == "blocked"
            assert "leader" in record.error_message
            
        # 4. Test with leader
        with patch("app.services.routing.commercial_infra_execution.is_current_leader", new_callable=AsyncMock) as mock_is_leader:
            mock_is_leader.return_value = True
            with patch("app.services.routing.commercial_infra_execution._active_lease_query", new_callable=AsyncMock) as mock_lease:
                mock_lease.return_value = MagicMock(id=uuid.uuid4())
                
                record = await svc.execute_simulation(db, sim.id, "mock", dry_run=False, confirm=True, approval_id=approval.id)
                assert record.status == "executed"
                assert record.dry_run is False

@pytest.mark.asyncio
async def test_rollback_mock(base_settings):
    with patch("app.services.routing.commercial_infra_execution.get_settings", return_value=base_settings):
        svc = CommercialInfraExecutionService()
        db = AsyncMock()
        record = CommercialExecutionRecord(
            id=uuid.uuid4(),
            simulation_id=uuid.uuid4(),
            adapter="mock",
            action_type="scale_up",
            target_scope="cluster",
            target_identifier="test",
            requested_action_json={},
            status="executed"
        )
        db.get.return_value = record
        
        rolled_back = await svc.rollback_execution(db, record.id)
        assert rolled_back.status == "rolled_back"

@pytest.mark.asyncio
async def test_kubernetes_adapter_unavailable_without_lib(base_settings):
    from app.services.routing.infra_adapters.kubernetes_adapter import KubernetesAdapter
    
    with patch("app.services.routing.infra_adapters.kubernetes_adapter.get_settings", return_value=base_settings):
        base_settings.commercial_k8s_execution_enabled = True
        adapter = KubernetesAdapter()
        assert adapter.validate_connection() is False
        
        sim = MagicMock()
        sim.simulation_type = "scale_up"
        result = await adapter.execute_action(sim, dry_run=True)
        assert result["status"] == "failed"
        assert "unavailable" in result["error"]
