import logging
import uuid
from typing import Any

from app.core.time import utc_now
from app.models.commercial.commercial_infra_simulation import CommercialInfrastructureSimulation
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def simulate_scale_up(
    db: AsyncSession, target_scope: str, target_identifier: str, action_details: dict[str, Any]
) -> CommercialInfrastructureSimulation:
    """
    Simulates a scale up action and estimates impacts.
    """
    # In a real implementation, this would use historical data and models
    # to predict impact. For Phase 21.1, we use heuristic estimation.

    nodes = action_details.get("nodes", 1)
    gpu_type = action_details.get("gpu_type", "RTX4090")

    # Heuristic: Each node adds X capacity, costs Y, and reduces SLA risk by Z.
    predicted_cost = nodes * 5.0  # Placeholder: 5 BRL per node/hour
    predicted_margin_impact = -predicted_cost * 0.2  # Heuristic

    simulation = CommercialInfrastructureSimulation(
        id=uuid.uuid4(),
        simulation_type="scale_up",
        target_scope=target_scope,
        target_identifier=target_identifier,
        requested_action_json=action_details,
        predicted_capacity_impact_json={"added_rpm": nodes * 100, "added_concurrency": nodes * 4},
        predicted_cost_impact_brl=predicted_cost,
        predicted_margin_impact_brl=predicted_margin_impact,
        predicted_sla_impact_json={"sla_risk_reduction_percent": min(10.0, nodes * 2.5)},
        predicted_queue_impact_json={"queue_depth_reduction": nodes * 10},
        predicted_latency_impact_json={"p95_reduction_ms": nodes * 50},
        blast_radius=estimate_blast_radius("scale_up", nodes),
        created_at=utc_now(),
    )

    db.add(simulation)
    return simulation


async def simulate_scale_down(
    db: AsyncSession, target_scope: str, target_identifier: str, action_details: dict[str, Any]
) -> CommercialInfrastructureSimulation:
    nodes = action_details.get("nodes", 1)

    predicted_cost_saving = nodes * 5.0
    predicted_margin_impact = predicted_cost_saving * 0.8  # Most saving goes to margin

    simulation = CommercialInfrastructureSimulation(
        id=uuid.uuid4(),
        simulation_type="scale_down",
        target_scope=target_scope,
        target_identifier=target_identifier,
        requested_action_json=action_details,
        predicted_capacity_impact_json={"removed_rpm": nodes * 100},
        predicted_cost_impact_brl=-predicted_cost_saving,
        predicted_margin_impact_brl=predicted_margin_impact,
        predicted_sla_impact_json={"sla_risk_increase_percent": nodes * 1.5},
        blast_radius=estimate_blast_radius("scale_down", nodes),
        created_at=utc_now(),
    )
    db.add(simulation)
    return simulation


async def simulate_reroute(
    db: AsyncSession, target_scope: str, target_identifier: str, action_details: dict[str, Any]
) -> CommercialInfrastructureSimulation:
    traffic_percent = action_details.get("traffic_percent", 10)

    simulation = CommercialInfrastructureSimulation(
        id=uuid.uuid4(),
        simulation_type="reroute",
        target_scope=target_scope,
        target_identifier=target_identifier,
        requested_action_json=action_details,
        predicted_cost_impact_brl=traffic_percent * 0.5,
        predicted_margin_impact_brl=-traffic_percent * 0.1,
        blast_radius="medium" if traffic_percent > 20 else "low",
        created_at=utc_now(),
    )
    db.add(simulation)
    return simulation


async def simulate_cluster_failover(
    db: AsyncSession, target_identifier: str, action_details: dict[str, Any]
) -> CommercialInfrastructureSimulation:
    simulation = CommercialInfrastructureSimulation(
        id=uuid.uuid4(),
        simulation_type="cluster_failover",
        target_scope="cluster",
        target_identifier=target_identifier,
        requested_action_json=action_details,
        predicted_cost_impact_brl=100.0,  # High cost for failover
        predicted_sla_impact_json={"risk": "critical"},
        blast_radius="critical",
        created_at=utc_now(),
    )
    db.add(simulation)
    return simulation


def estimate_blast_radius(action_type: str, magnitude: float) -> str:
    if action_type == "cluster_failover":
        return "critical"

    if action_type == "scale_up":
        if magnitude > 10:
            return "high"
        if magnitude > 5:
            return "medium"
        return "low"

    if action_type == "scale_down":
        if magnitude > 5:
            return "high"
        if magnitude > 2:
            return "medium"
        return "low"

    return "low"


async def summarize_simulation(simulation: CommercialInfrastructureSimulation) -> dict[str, Any]:
    return {
        "id": str(simulation.id),
        "type": simulation.simulation_type,
        "status": simulation.safety_gate_status,
        "blast_radius": simulation.blast_radius,
        "impacts": {
            "cost_brl": simulation.predicted_cost_impact_brl,
            "margin_brl": simulation.predicted_margin_impact_brl,
            "sla": simulation.predicted_sla_impact_json,
        },
    }
