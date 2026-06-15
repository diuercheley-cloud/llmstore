import pytest
from app.services.governance.policy_registry import PolicyRegistryService
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_create_policy_bundle(session: AsyncSession):
    service = PolicyRegistryService()
    rules = {
        "routing": {"force_local_only": True},
        "billing": {"wallet_debit_enabled": False},
        "qos": {"max_priority": 3},
    }

    bundle = await service.create_policy_bundle(
        db=session,
        bundle_name="Test Bundle",
        bundle_version="1.0.0",
        bundle_type="routing",
        rules_json=rules,
        mode="dry_run",
    )

    assert bundle.bundle_name == "Test Bundle"
    assert bundle.status == "draft"
    assert bundle.immutable_hash is not None
    assert bundle.rules_json == rules


@pytest.mark.asyncio
async def test_publish_and_activate_policy_bundle(session: AsyncSession):
    service = PolicyRegistryService()
    rules = {"routing": {"force_local_only": True}}

    bundle = await service.create_policy_bundle(
        db=session,
        bundle_name="Publish Test",
        bundle_version="1.1.0",
        bundle_type="global",
        rules_json=rules,
    )

    await service.publish_policy_bundle(session, bundle.id, "admin@example.com")
    assert bundle.status == "published"
    assert bundle.published_at is not None

    await service.activate_policy_bundle(session, bundle.id, "admin@example.com")
    assert bundle.status == "active"
    assert bundle.activated_at is not None


@pytest.mark.asyncio
async def test_rollback_policy_bundle(session: AsyncSession):
    service = PolicyRegistryService()

    # Create and activate v1
    v1 = await service.create_policy_bundle(session, "V1", "1.0", "routing", {"r": 1})
    await service.publish_policy_bundle(session, v1.id, "admin")
    await service.activate_policy_bundle(session, v1.id, "admin")

    # Create and activate v2
    v2 = await service.create_policy_bundle(session, "V2", "2.0", "routing", {"r": 2})
    await service.publish_policy_bundle(session, v2.id, "admin")
    await service.activate_policy_bundle(session, v2.id, "admin")

    assert v1.status == "deprecated"
    assert v2.status == "active"

    # Rollback v2
    await service.rollback_policy_bundle(session, v2.id, "admin")

    assert v2.status == "rolled_back"
    assert v1.status == "active"
