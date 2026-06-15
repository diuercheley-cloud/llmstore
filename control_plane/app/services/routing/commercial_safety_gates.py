import logging
from typing import Any

from app.core.config import get_settings
from app.models.commercial.commercial_infra_simulation import (
    CommercialInfrastructureSimulation,
    CommercialSafetyPolicy,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def validate_simulation_against_policy(
    db: AsyncSession, simulation: CommercialInfrastructureSimulation, policy_name: str = "default"
) -> tuple[str, str | None]:
    """
    Validates a simulation against a safety policy.
    Returns (status, reason).
    """
    settings = get_settings()
    if not settings.commercial_safety_gates_enabled:
        return "allowed", None

    # Fetch policy
    stmt = select(CommercialSafetyPolicy).where(CommercialSafetyPolicy.policy_name == policy_name)
    result = await db.execute(stmt)
    policy = result.scalar_one_or_none()

    if not policy or not policy.enabled:
        # Fallback to hardcoded settings if policy not found
        return await validate_against_defaults(simulation)

    # 1. Cost increase check
    if simulation.predicted_cost_impact_brl > 0:
        # Assuming we have a base cost to compare with, or just using absolute limit
        # For this simulation, let's use percentage if available or just limits
        if simulation.predicted_cost_impact_brl > 1000.0:  # Absolute limit example
            return "blocked", "Cost increase exceeds absolute safety limit"

    # 2. Margin drop check
    if simulation.predicted_margin_impact_brl < -100.0:
        return "blocked", "Predicted margin drop is too high"

    # 3. SLA risk check
    sla_impact = simulation.predicted_sla_impact_json or {}
    if (
        sla_impact.get("risk") == "critical"
        or sla_impact.get("sla_risk_increase_percent", 0)
        > policy.max_predicted_sla_violation_percent
    ):
        return "blocked", "SLA risk exceeds policy limits"

    # 4. Blast radius check
    if requires_manual_approval(simulation, policy):
        return (
            "requires_approval",
            f"Blast radius {simulation.blast_radius} requires manual approval",
        )

    # 5. Type specific checks
    if simulation.simulation_type == "scale_down" and not policy.allow_scale_down:
        return "blocked", "Scale down is disabled by policy"

    if simulation.simulation_type == "cluster_failover" and not policy.allow_cluster_failover:
        return "requires_approval", "Cluster failover always requires approval"

    return "allowed", None


async def validate_against_defaults(
    simulation: CommercialInfrastructureSimulation,
) -> tuple[str, str | None]:
    settings = get_settings()

    if simulation.blast_radius == "critical":
        if settings.commercial_require_approval_for_critical:
            return "requires_approval", "Critical blast radius requires approval"
        return "blocked", "Critical actions blocked by default"

    if simulation.predicted_cost_impact_brl > 50.0:  # Default threshold
        return "requires_approval", "High cost impact requires approval"

    return "allowed", None


def requires_manual_approval(
    simulation: CommercialInfrastructureSimulation, policy: CommercialSafetyPolicy
) -> bool:
    radius_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    policy_limit = radius_order.get(policy.require_manual_approval_above_blast_radius, 1)
    sim_radius = radius_order.get(simulation.blast_radius, 0)

    return sim_radius >= policy_limit


def classify_blast_radius(impact_factors: dict[str, Any]) -> str:
    # Logic to classify blast radius based on nodes, clusters, traffic affected
    nodes = impact_factors.get("nodes_affected", 0)
    clusters = impact_factors.get("clusters_affected", 0)

    if clusters > 1 or nodes > 20:
        return "critical"
    if clusters == 1 or nodes > 10:
        return "high"
    if nodes > 2:
        return "medium"
    return "low"
