import pytest
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.operations.adapter_sandbox import (
    AdapterManifest,
    AdapterSandboxRun,
    AdapterSandboxStepResult,
    AdapterSandboxPolicyViolation,
    AdapterSandboxReceipt,
)

@pytest.mark.asyncio
class TestAdapterSandboxModels:
    async def test_create_adapter_manifest(self, session: AsyncSession):
        client_id = uuid.uuid4()
        manifest = AdapterManifest(
            client_id=client_id,
            adapter_name="test_adapter",
            adapter_version="1.0.0",
            adapter_type="simulation",
            capabilities_json={"allowed": ["restart"]},
            denied_capabilities_json={"denied": ["shell"]},
            manifest_hash="hash",
            immutable_hash="imm_hash"
        )
        session.add(manifest)
        await session.commit()

        result = await session.execute(select(AdapterManifest).where(AdapterManifest.client_id == client_id))
        saved = result.scalars().one()
        assert saved.adapter_name == "test_adapter"
        assert saved.sandbox_required is True

    async def test_create_sandbox_run(self, session: AsyncSession):
        client_id = uuid.uuid4()
        manifest_id = uuid.uuid4()
        
        # Satisfaction of FKs for test
        manifest = AdapterManifest(
            id=manifest_id, client_id=client_id, adapter_name="m", adapter_version="v", adapter_type="t",
            capabilities_json={}, denied_capabilities_json={}, manifest_hash="h", immutable_hash="ih"
        )
        session.add(manifest)
        
        run = AdapterSandboxRun(
            client_id=client_id,
            manifest_id=manifest_id,
            sandbox_mode="simulation",
            status="pending",
            input_hash="ih",
            immutable_hash="ph"
        )
        session.add(run)
        await session.commit()

        result = await session.execute(select(AdapterSandboxRun).where(AdapterSandboxRun.client_id == client_id))
        saved = result.scalars().one()
        assert saved.sandbox_mode == "simulation"
