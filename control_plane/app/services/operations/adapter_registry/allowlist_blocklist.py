
from app.models.operations.adapter_registry import (
    AdapterRegistryAllowlistEntry,
    AdapterRegistryBlocklistEntry,
    SignedAdapterRegistryEntry,
)
from app.services.operations.adapter_registry.hash_utils import sha256_hex
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class AdapterRegistryListService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_to_allowlist(self, entry: SignedAdapterRegistryEntry, reason: str) -> AdapterRegistryAllowlistEntry:
        # Deterministic immutable_hash
        immutable_hash = sha256_hex(f"allow_{entry.client_id}_{entry.manifest_hash}")
        
        item = AdapterRegistryAllowlistEntry(
            client_id=entry.client_id,
            adapter_name=entry.adapter_name,
            adapter_version=entry.adapter_version,
            manifest_hash=entry.manifest_hash,
            reason=reason,
            immutable_hash=immutable_hash,
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def add_to_blocklist(self, entry: SignedAdapterRegistryEntry, reason: str) -> AdapterRegistryBlocklistEntry:
        # Deterministic immutable_hash
        immutable_hash = sha256_hex(f"block_{entry.client_id}_{entry.manifest_hash}")
        
        item = AdapterRegistryBlocklistEntry(
            client_id=entry.client_id,
            adapter_name=entry.adapter_name,
            adapter_version=entry.adapter_version,
            manifest_hash=entry.manifest_hash,
            reason=reason,
            immutable_hash=immutable_hash,
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def is_allowed(self, entry: SignedAdapterRegistryEntry) -> bool:
        stmt = select(AdapterRegistryAllowlistEntry).where(
            AdapterRegistryAllowlistEntry.client_id == entry.client_id,
            AdapterRegistryAllowlistEntry.manifest_hash == entry.manifest_hash
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def is_blocked(self, entry: SignedAdapterRegistryEntry) -> bool:
        stmt = select(AdapterRegistryBlocklistEntry).where(
            AdapterRegistryBlocklistEntry.client_id == entry.client_id,
            AdapterRegistryBlocklistEntry.manifest_hash == entry.manifest_hash
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def explain_list_status(self, entry: SignedAdapterRegistryEntry) -> str:
        if await self.is_blocked(entry):
            return "Entry is explicitly blocked"
        if await self.is_allowed(entry):
            return "Entry is explicitly allowed"
        return "Entry is not in any explicit list"
