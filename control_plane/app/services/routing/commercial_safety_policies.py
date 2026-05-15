import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.commercial_infra_simulation import CommercialSafetyPolicy

async def ensure_default_safety_policies(session: AsyncSession) -> None:
    stmt = select(CommercialSafetyPolicy).where(CommercialSafetyPolicy.policy_name == "default")
    result = await session.execute(stmt)
    if result.scalar_one_or_none():
        return

    default_policy = CommercialSafetyPolicy(
        id=uuid.uuid4(),
        policy_name="default",
        enabled=True,
        max_predicted_cost_increase_percent=20.0,
        max_predicted_margin_drop_percent=10.0,
        max_predicted_sla_violation_percent=5.0,
        max_nodes_affected=5,
        max_clusters_affected=1,
        require_manual_approval_above_blast_radius="medium",
        allow_scale_down=True,
        allow_scale_up=True,
        allow_cluster_failover=False,
        allow_cross_region_routing=False
    )
    session.add(default_policy)
