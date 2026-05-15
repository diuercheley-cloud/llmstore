import pytest
import uuid
from datetime import timedelta
from unittest.mock import MagicMock

from app.core.time import utc_now
from app.models.commercial_crypto_trust import (
    CommercialKMSProvider,
    CommercialKeyMaterial,
    CommercialKeyRotationSchedule,
    CryptoProviderType,
    KeyUsageStatus
)
from app.services.security.key_rotation import KeyRotationService


@pytest.fixture
def mock_db_session():
    db = MagicMock()
    return db

@pytest.fixture
def key_rotation_service(mock_db_session):
    return KeyRotationService(mock_db_session)

@pytest.mark.asyncio
async def test_rotate_key_success(key_rotation_service, mock_db_session):
    provider_id = uuid.uuid4()
    old_key_id = uuid.uuid4()
    schedule_id = uuid.uuid4()

    mock_provider = CommercialKMSProvider(id=provider_id, provider_type=CryptoProviderType.LOCAL_KEYSTORE, is_active=True)
    mock_old_key = CommercialKeyMaterial(id=old_key_id, provider_id=provider_id, tenant_id=None, key_alias="root_key", key_type="RSA-2048", status=KeyUsageStatus.ACTIVE)
    mock_schedule = CommercialKeyRotationSchedule(id=schedule_id, key_id=old_key_id, rotation_interval_days=30, next_rotation_at=utc_now() - timedelta(days=1), key=mock_old_key)

    # 1. schedule lookup
    # 2. provider lookup
    mock_db_session.query.return_value.filter.return_value.first.side_effect = [mock_schedule, mock_provider]

    new_key = await key_rotation_service.rotate_key(schedule_id)

    assert new_key.key_alias.startswith("root_key_rot_")
    assert new_key.status == KeyUsageStatus.ACTIVE
    assert mock_old_key.status == KeyUsageStatus.ROTATED
    assert mock_schedule.key_id == new_key.id
    assert mock_db_session.commit.called
