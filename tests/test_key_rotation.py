import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import Settings
from app.services.security.tenant_encryption import TenantEncryptionService
from app.models.commercial_encryption import CommercialTenantEncryptionKey

@pytest.fixture
def encryption_service(settings: Settings):
    return TenantEncryptionService(settings)

@pytest.mark.asyncio
async def test_key_rotation(session: AsyncSession, encryption_service: TenantEncryptionService):
    client_id = uuid.uuid4()
    
    # 1. Create initial key
    key1 = await encryption_service.create_tenant_key(session, client_id)
    key1_id = key1.id
    
    # 2. Rotate
    key2 = await encryption_service.rotate_tenant_key(session, key1_id)
    assert key2.id != key1_id
    assert key2.client_id == client_id
    
    # 3. Check old key status
    await session.refresh(key1)
    assert key1.key_status == "deprecated"
    assert key1.rotated_at is not None

@pytest.mark.asyncio
async def test_key_revocation(session: AsyncSession, encryption_service: TenantEncryptionService):
    client_id = uuid.uuid4()
    key = await encryption_service.create_tenant_key(session, client_id)
    
    # Encrypt something
    artifact = await encryption_service.encrypt_payload(session, client_id, "secret", "test", "res")
    
    # Revoke key
    await encryption_service.revoke_tenant_key(session, key.id)
    
    # Decrypt should fail
    with pytest.raises(ValueError, match="Key is revoked"):
        await encryption_service.decrypt_payload(session, artifact)
