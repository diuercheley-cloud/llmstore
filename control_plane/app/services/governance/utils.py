import uuid
from typing import Any

from app.services.governance.policy_engine import PolicyEngineService
from app.services.governance.policy_registry import PolicyRegistryService
from sqlalchemy.ext.asyncio import AsyncSession


async def get_effective_policy_constraints(
    db: AsyncSession,
    bundle_type: str,
    client_id: uuid.UUID | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Helper to get effective constraints for a given bundle type and client.
    Can be used by routing, QoS, and billing services to enforce policies.
    """
    registry = PolicyRegistryService()
    engine = PolicyEngineService()

    bundle = await registry.get_active_policy_bundle(db, bundle_type, client_id)
    if not bundle:
        # Fallback to global policy if client-specific not found
        if client_id:
            bundle = await registry.get_active_policy_bundle(db, bundle_type, None)

    if not bundle or bundle.mode == "disabled":
        return {}

    constraints = await engine.evaluate_rules(bundle, context or {})
    return {
        "mode": bundle.mode,
        "bundle_id": str(bundle.id),
        "bundle_version": bundle.bundle_version,
        "constraints": constraints,
    }
