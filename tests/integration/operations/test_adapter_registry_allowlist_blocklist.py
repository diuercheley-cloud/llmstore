import uuid

import pytest
from app.models.operations.adapter_registry import SignedAdapterRegistryEntry
from app.services.operations.adapter_registry.allowlist_blocklist import AdapterRegistryListService
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
class TestAdapterRegistryAllowlistBlocklist:
    async def test_allowlist_blocklist_flow(self, session: AsyncSession):
        client_id = uuid.uuid4()
        entry = SignedAdapterRegistryEntry(
            client_id=client_id,
            adapter_name="test_adapter",
            adapter_version="1.0.0",
            manifest_hash="hash_abc",
            registry_hash="rhash",
            signature="sig",
            immutable_hash="imm_h"
        )
        
        service = AdapterRegistryListService(session)
        
        assert await service.is_allowed(entry) is False
        assert await service.is_blocked(entry) is False
        
        await service.add_to_allowlist(entry, reason="trusted")
        assert await service.is_allowed(entry) is True
        assert "explicitly allowed" in await service.explain_list_status(entry)
        
        await service.add_to_blocklist(entry, reason="malicious")
        assert await service.is_blocked(entry) is True
        assert "explicitly blocked" in await service.explain_list_status(entry)
