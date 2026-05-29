"""Plugin signature persistence helpers."""

# Owner: platform-ops
"""Plugin signature persistence helpers."""

# Owner: platform-ops
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.agent_catalog import PluginSignature

class PluginSignatureService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_signature(self, plugin_entry_id: uuid.UUID, signer: str, signature: str):
        sig = PluginSignature(
            plugin_entry_id=plugin_entry_id,
            signer_identity=signer,
            signature_data=signature
        )
        self.db.add(sig)
        await self.db.commit()
        return sig
