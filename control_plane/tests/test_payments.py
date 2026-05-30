import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.billing.payments.pix_service import PixService
from app.services.billing.payments.card_service import CardService
from app.services.billing.payments.payment_reconciliation import PaymentReconciliationService
from app.core.config import get_settings

@pytest.mark.asyncio
async def test_mock_pix_creates_qr():
    session = AsyncMock()
    
    # Enable PIX
    with patch("app.services.billing.payments.pix_service.settings.pix_payment_enabled", True):
        res = await PixService.create_payment(session, uuid.uuid4(), 1000)
        assert "qr_code" in res
        assert res["status"] == "pending"

@pytest.mark.asyncio
async def test_provider_disabled_blocks():
    session = AsyncMock()
    
    # Disable PIX
    with patch("app.services.billing.payments.pix_service.settings.pix_payment_enabled", False):
        with pytest.raises(ValueError, match="PIX payments are disabled"):
            await PixService.create_payment(session, uuid.uuid4(), 1000)

@pytest.mark.asyncio
async def test_webhook_validation_failure():
    session = AsyncMock()
    
    # Mock provider validation to fail
    with patch("app.services.billing.payments.mock_payment_provider.MockPaymentProvider.validate_webhook", return_value=False):
        success = await PaymentReconciliationService.process_webhook(session, "mock", b"payload", "invalid_sig")
        assert success is False

@pytest.mark.asyncio
async def test_card_payment_mock():
    session = AsyncMock()
    
    with patch("app.services.billing.payments.card_service.settings.card_payment_enabled", True):
        res = await CardService.create_payment(session, uuid.uuid4(), 5000, "tok_visa")
        assert res["status"] == "succeeded"
        assert res["last4"] == "4242"
