import uuid

import pytest
from app.models.operations.adapter_sandbox import AdapterManifest
from app.services.operations.adapter_registry.registry_service import SignedAdapterRegistryService
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
class TestSignedAdapterRegistryService:
    async def test_register_entry(self, session: AsyncSession):
        client_id = uuid.uuid4()
        manifest = AdapterManifest(
            client_id=client_id,
            adapter_name="test_adapter",
            adapter_version="1.0.0",
            adapter_type="remediation",
            manifest_hash="mhash",
            immutable_hash="imm_mhash",
            capabilities_json={"requested": []},
            denied_capabilities_json={"denied": []}
        )
        session.add(manifest)
        await session.flush()
        
        service = SignedAdapterRegistryService(session)
        entry = await service.register_entry(manifest)
        
        assert entry.adapter_name == "test_adapter"
        assert entry.registry_status == "draft"
        assert isinstance(entry.signature, str) and len(entry.signature) > 0

    async def test_lifecycle_transitions(self, session: AsyncSession):
        client_id = uuid.uuid4()
        manifest = AdapterManifest(
            client_id=client_id,
            adapter_name="test_adapter",
            adapter_version="1.0.0",
            adapter_type="remediation",
            manifest_hash="mhash2",
            immutable_hash="imm_mhash2",
            capabilities_json={"requested": []},
            denied_capabilities_json={"denied": []}
        )
        session.add(manifest)
        await session.flush()
        
        service = SignedAdapterRegistryService(session)
        entry = await service.register_entry(manifest)
        
        await service.submit_entry(entry, decided_by="admin@test.com")
        assert entry.registry_status == "submitted"
        
        await service.approve_entry(entry, approved_by="admin@test.com")
        assert entry.registry_status == "approved"
        assert entry.approved_by == "admin@test.com"
        
        await service.revoke_entry(entry, reason="security risk", decided_by="admin@test.com")
        assert entry.registry_status == "revoked"
        assert entry.revoked_reason == "security risk"
