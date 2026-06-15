import uuid
from unittest.mock import MagicMock

import pytest
from app.models.commercial.commercial_crypto_trust import (
    CommercialKeyMaterial,
    CommercialKMSProvider,
    CommercialSigningProfile,
    CryptoProviderType,
    KeyUsageStatus,
)
from app.services.security.signing_service import SigningService


@pytest.fixture
def mock_db_session():
    db = MagicMock()
    return db


@pytest.fixture
def signing_service(mock_db_session):
    return SigningService(mock_db_session)


@pytest.mark.asyncio
async def test_sign_payload_success(signing_service, mock_db_session):
    provider_id = uuid.uuid4()
    key_id = uuid.uuid4()
    profile_id = uuid.uuid4()

    mock_profile = CommercialSigningProfile(id=profile_id, key_id=key_id, algorithm="RSA-SHA256")
    mock_key = CommercialKeyMaterial(
        id=key_id,
        provider_id=provider_id,
        status=KeyUsageStatus.ACTIVE,
        encrypted_key_blob="mock_blob",
    )
    mock_provider = CommercialKMSProvider(
        id=provider_id, provider_type=CryptoProviderType.VAULT, is_active=True
    )

    # signing_service.get_signing_profile -> profile
    # kms_runtime.get_key_material -> key
    # kms_runtime.get_provider_config -> provider
    mock_db_session.query.return_value.filter.return_value.first.side_effect = [
        mock_profile,
        mock_key,
        mock_provider,
    ]

    payload = b"important payload"
    signature = await signing_service.sign_payload(profile_id, payload)

    assert signature.startswith(b"VAULT_SIG:")
    assert b"important payload" in signature


@pytest.mark.asyncio
async def test_verify_signature_success(signing_service, mock_db_session):
    provider_id = uuid.uuid4()
    key_id = uuid.uuid4()
    profile_id = uuid.uuid4()

    mock_profile = CommercialSigningProfile(id=profile_id, key_id=key_id, algorithm="RSA-SHA256")
    mock_key = CommercialKeyMaterial(
        id=key_id,
        provider_id=provider_id,
        status=KeyUsageStatus.ACTIVE,
        encrypted_key_blob="mock_blob",
    )
    mock_provider = CommercialKMSProvider(
        id=provider_id, provider_type=CryptoProviderType.HSM, is_active=True
    )

    mock_db_session.query.return_value.filter.return_value.first.side_effect = [
        mock_profile,
        mock_key,
        mock_provider,
    ]

    payload = b"data"
    signature = b"HSM_SIG:data"

    is_valid = await signing_service.verify_signature(profile_id, payload, signature)
    assert is_valid is True
