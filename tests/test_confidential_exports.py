import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import Settings
from app.services.security.tenant_encryption import TenantEncryptionService

@pytest.fixture
def encryption_service(settings: Settings):
    return TenantEncryptionService(settings)

@pytest.mark.asyncio
async def test_export_redaction(session: AsyncSession, encryption_service: TenantEncryptionService, settings: Settings):
    client_id = uuid.uuid4()
    data = {"secret": "api_key=12345", "info": "public"}
    
    # Configure to redact instead of block
    settings.commercial_tenant_encryption_block_restricted_exports = False
    
    result = await encryption_service.confidential_export_control(session, client_id, data)
    assert "[REDACTED: RESTRICTED]" in result["secret"]
    assert result["info"] == "public"

@pytest.mark.asyncio
async def test_export_encryption_required(session: AsyncSession, encryption_service: TenantEncryptionService, settings: Settings):
    client_id = uuid.uuid4()
    data = {"user_email": "test@example.com"}
    
    # Configure to require encryption for confidential
    settings.commercial_tenant_encryption_require_encrypted_exports = True
    
    result = await encryption_service.confidential_export_control(session, client_id, data)
    assert "[ENCRYPTED: CONFIDENTIAL]" in result["user_email"]
