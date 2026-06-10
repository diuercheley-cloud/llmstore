from unittest.mock import AsyncMock, MagicMock

import pytest
from app.models.commercial.commercial_infra_simulation import (
    CommercialInfrastructureSimulation,
    CommercialSafetyPolicy,
)
from app.services.routing.commercial_infra_simulation import (
    estimate_blast_radius,
    simulate_scale_down,
    simulate_scale_up,
)
from app.services.routing.commercial_safety_gates import (
    requires_manual_approval,
    validate_simulation_against_policy,
)


@pytest.mark.asyncio
async def test_simulate_scale_up():
    db = AsyncMock()
    db.add = MagicMock()
    sim = await simulate_scale_up(db, "cluster", "cluster-east", {"nodes": 2})
    
    assert sim.simulation_type == "scale_up"
    assert sim.predicted_cost_impact_brl == 10.0
    assert sim.blast_radius == "low"
    db.add.assert_called_once()

@pytest.mark.asyncio
async def test_simulate_scale_down():
    db = AsyncMock()
    db.add = MagicMock()
    sim = await simulate_scale_down(db, "cluster", "cluster-east", {"nodes": 3})
    
    assert sim.simulation_type == "scale_down"
    assert sim.predicted_cost_impact_brl == -15.0
    assert sim.blast_radius == "medium"
    db.add.assert_called_once()

def test_estimate_blast_radius():
    assert estimate_blast_radius("scale_up", 1) == "low"
    assert estimate_blast_radius("scale_up", 6) == "medium"
    assert estimate_blast_radius("scale_up", 11) == "high"
    assert estimate_blast_radius("cluster_failover", 1) == "critical"

@pytest.mark.asyncio
async def test_validate_blocked_by_cost():
    db = AsyncMock()
    sim = CommercialInfrastructureSimulation(
        predicted_cost_impact_brl=1500.0,
        simulation_type="scale_up",
        blast_radius="low",
        predicted_sla_impact_json={}
    )
    
    # Mock policy
    policy = CommercialSafetyPolicy(
        policy_name="default",
        enabled=True,
        max_predicted_cost_increase_percent=20.0,
        max_predicted_sla_violation_percent=5.0,
        require_manual_approval_above_blast_radius="medium"
    )
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = policy
    db.execute.return_value = mock_result
    
    status, reason = await validate_simulation_against_policy(db, sim)
    assert status == "blocked"
    assert "Cost increase exceeds" in reason

def test_requires_manual_approval():
    policy = CommercialSafetyPolicy(require_manual_approval_above_blast_radius="medium")
    
    sim_low = CommercialInfrastructureSimulation(blast_radius="low")
    sim_medium = CommercialInfrastructureSimulation(blast_radius="medium")
    sim_critical = CommercialInfrastructureSimulation(blast_radius="critical")
    
    assert requires_manual_approval(sim_low, policy) is False
    assert requires_manual_approval(sim_medium, policy) is True
    assert requires_manual_approval(sim_critical, policy) is True
