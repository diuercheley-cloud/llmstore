import pytest
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.operations.adapter_registry import (
    SignedAdapterRegistryEntry,
    AdapterRegistryPolicy,
    AdapterRegistryDecision,
    AdapterRegistryReceipt,
    AdapterRegistryBlocklistEntry,
    AdapterRegistryAllowlistEntry,
)
from app.models.operations.adapter_sandbox import AdapterManifest

@pytest.mark.asyncio
class TestAdapterRegistryModels:
    async def test_create_registry_entry(self, session: AsyncSession):
        client_id = uuid.uuid4()
        manifest_id = uuid.uuid4()
        entry = SignedAdapterRegistryEntry(
            client_id=client_id,
            adapter_name="test_adapter",
            adapter_version="1.0.0",
            adapter_type="remediation",
            manifest_id=manifest_id,
            manifest_hash="hash123",
            registry_status="draft",
            registry_hash="reg_hash123",
            signature="sig_abc",
            immutable_hash="imm_hash123"
        )
        session.add(entry)
        await session.commit()
        
        stmt = select(SignedAdapterRegistryEntry).where(SignedAdapterRegistryEntry.id == entry.id)
        result = await session.execute(stmt)
        stored = result.scalar_one()
        assert stored.adapter_name == "test_adapter"
        assert stored.registry_status == "draft"

    async def test_create_registry_policy(self, session: AsyncSession):
        client_id = uuid.uuid4()
        policy = AdapterRegistryPolicy(
            client_id=client_id,
            policy_name="Strict Policy",
            allowed_adapter_types_json={"allowed_types": ["remediation"]},
            denied_capabilities_json={"denied": ["network"]},
            require_sandbox=True,
            immutable_hash="pol_imm_hash123"
        )
        session.add(policy)
        await session.commit()
        
        stmt = select(AdapterRegistryPolicy).where(AdapterRegistryPolicy.id == policy.id)
        result = await session.execute(stmt)
        stored = result.scalar_one()
        assert stored.policy_name == "Strict Policy"
        assert stored.require_sandbox is True
