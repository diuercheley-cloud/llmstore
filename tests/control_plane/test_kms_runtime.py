import uuid
from unittest.mock import MagicMock

import pytest
from app.models.commercial.commercial_crypto_trust import (
    CommercialKeyMaterial,
    CommercialKMSProvider,
    CryptoProviderType,
    KeyUsageStatus,
)
from app.services.security.kms_runtime import KMSRuntime, KMSRuntimeError


@pytest.fixture
def mock_db_session():
    db = MagicMock()
    return db

@pytest.fixture
def kms_runtime(mock_db_session):
    return KMSRuntime(mock_db_session)

@pytest.mark.asyncio
async def test_encrypt_success(kms_runtime, mock_db_session):
    provider_id = uuid.uuid4()
    key_id = uuid.uuid4()

    mock_provider = CommercialKMSProvider(id=provider_id, provider_type=CryptoProviderType.LOCAL_KEYSTORE, is_active=True)
    mock_key = CommercialKeyMaterial(id=key_id, provider_id=provider_id, status=KeyUsageStatus.ACTIVE, encrypted_key_blob="mock_blob")

    # Setup DB mocks
    mock_db_session.query.return_value.filter.return_value.first.side_effect = [mock_key, mock_provider]

    plaintext = b"secret data"
    ciphertext = await kms_runtime.encrypt(key_id, plaintext)

    assert ciphertext.startswith(b"ENC:")
    assert b"secret data" in ciphertext

@pytest.mark.asyncio
async def test_encrypt_inactive_provider(kms_runtime, mock_db_session):
    provider_id = uuid.uuid4()
    key_id = uuid.uuid4()

    mock_provider = CommercialKMSProvider(id=provider_id, provider_type=CryptoProviderType.LOCAL_KEYSTORE, is_active=False)
    mock_key = CommercialKeyMaterial(id=key_id, provider_id=provider_id, status=KeyUsageStatus.ACTIVE, encrypted_key_blob="mock_blob")

    # Setup DB mocks
    mock_db_session.query.return_value.filter.return_value.first.side_effect = [mock_key, mock_provider]

    with pytest.raises(KMSRuntimeError, match="not active"):
        await kms_runtime.encrypt(key_id, b"secret data")

@pytest.mark.asyncio
async def test_decrypt_success(kms_runtime, mock_db_session):
    provider_id = uuid.uuid4()
    key_id = uuid.uuid4()

    mock_provider = CommercialKMSProvider(id=provider_id, provider_type=CryptoProviderType.LOCAL_KEYSTORE, is_active=True)
    mock_key = CommercialKeyMaterial(id=key_id, provider_id=provider_id, status=KeyUsageStatus.ACTIVE, encrypted_key_blob="mock_blob")

    # Setup DB mocks
    mock_db_session.query.return_value.filter.return_value.first.side_effect = [mock_key, mock_provider]

    ciphertext = b"ENC:secret data"
    plaintext = await kms_runtime.decrypt(key_id, ciphertext)

    assert plaintext == b"secret data"
