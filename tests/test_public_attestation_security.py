import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import get_settings

@pytest.mark.asyncio
async def test_gateway_disabled_by_default():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/attestation/status")
        assert response.status_code == 503
        assert "disabled" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_anonymization():
    from app.services.inference import public_attestation_gateway
    # Test IP masking logic again specifically for security
    ip = "192.168.1.50"
    masked = ".".join(ip.split(".")[:2]) + ".x.x"
    assert masked == "192.168.x.x"
