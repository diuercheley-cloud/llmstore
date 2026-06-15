import uuid

import pytest
from app.core.config import Settings
from app.services.security.tenant_encryption import TenantEncryptionService
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def encryption_service(settings: Settings):
    return TenantEncryptionService(settings)


@pytest.mark.asyncio
async def test_encrypt_decrypt_cycle(
    session: AsyncSession, encryption_service: TenantEncryptionService
):
    client_id = uuid.uuid4()
    payload = "this is a secret message"

    # 1. Encrypt
    artifact = await encryption_service.encrypt_payload(
        session,
        client_id,
        payload,
        artifact_type="test",
        resource_type="test_resource",
        resource_id="res_123",
    )

    assert artifact.encryption_mode == "envelope"
    assert artifact.encrypted_payload != payload

    # 2. Decrypt
    decrypted = await encryption_service.decrypt_payload(session, artifact)
    assert decrypted == payload


@pytest.mark.asyncio
async def test_key_isolation(session: AsyncSession, encryption_service: TenantEncryptionService):
    client_a = uuid.uuid4()
    client_b = uuid.uuid4()
    payload = "secret"

    art_a = await encryption_service.encrypt_payload(session, client_a, payload, "test", "res")
    art_b = await encryption_service.encrypt_payload(session, client_b, payload, "test", "res")

    assert art_a.key_id != art_b.key_id

    # Decrypting A with its key should work
    assert await encryption_service.decrypt_payload(session, art_a) == payload


@pytest.mark.asyncio
async def test_classification(encryption_service: TenantEncryptionService):
    assert await encryption_service.classify_sensitive_payload("public info") == "internal"
    assert (
        await encryption_service.classify_sensitive_payload("my email is test@example.com")
        == "confidential"
    )
    assert (
        await encryption_service.classify_sensitive_payload("the api_key is 12345") == "restricted"
    )


@pytest.mark.asyncio
async def test_confidential_export_blocked(
    session: AsyncSession, encryption_service: TenantEncryptionService
):
    client_id = uuid.uuid4()
    data = {"name": "John Doe", "api_key": "sk-12345", "email": "john@example.com"}

    # Block restricted
    result = await encryption_service.confidential_export_control(session, client_id, data)
    assert result["api_key"] == "[BLOCK: RESTRICTED]"
    assert result["name"] == "John Doe"
    assert "john@example.com" in result["email"]  # confidential not blocked by default
