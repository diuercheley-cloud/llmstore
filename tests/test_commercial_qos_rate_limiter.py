import uuid
import pytest
from app.services.routing.qos_rate_limiter import QoSRateLimiter

@pytest.mark.asyncio
async def test_qos_rate_limiter_basic(redis_client, settings):
    rl = QoSRateLimiter(redis_client)
    client_id = uuid.uuid4()
    
    settings.commercial_qos_rate_limiting_enabled = True
    settings.commercial_qos_rate_limit_mode = "enforce"
    settings.commercial_qos_free_rpm = 2
    
    # 1st request
    allowed, status, _ = await rl.check_rate_limit(client_id, "Free", "model")
    assert allowed is True
    assert status == "allowed"
    
    # 2nd request
    allowed, status, _ = await rl.check_rate_limit(client_id, "Free", "model")
    assert allowed is True
    assert status == "allowed"
    
    # 3rd request (limited)
    allowed, status, reason = await rl.check_rate_limit(client_id, "Free", "model")
    assert allowed is False
    assert status == "rejected"
    assert "limit reached" in reason

@pytest.mark.asyncio
async def test_qos_rate_limiter_report_only(redis_client, settings):
    rl = QoSRateLimiter(redis_client)
    client_id = uuid.uuid4()
    
    settings.commercial_qos_rate_limiting_enabled = True
    settings.commercial_qos_rate_limit_mode = "report_only"
    settings.commercial_qos_free_rpm = 1
    
    # 1st request
    allowed, status, _ = await rl.check_rate_limit(client_id, "Free", "model")
    assert allowed is True
    
    # 2nd request (throttled but allowed)
    allowed, status, reason = await rl.check_rate_limit(client_id, "Free", "model")
    assert allowed is True
    assert status == "throttled"
    assert "limit reached" in reason

@pytest.mark.asyncio
async def test_qos_rate_limiter_tier_thresholds(redis_client, settings):
    rl = QoSRateLimiter(redis_client)
    client_free = uuid.uuid4()
    client_ent = uuid.uuid4()
    
    settings.commercial_qos_free_rpm = 1
    settings.commercial_qos_enterprise_rpm = 100
    
    # Free client reaches 1 RPM quickly
    await rl.check_rate_limit(client_free, "Free", "model")
    allowed, _, _ = await rl.check_rate_limit(client_free, "Free", "model")
    assert allowed is (settings.commercial_qos_rate_limit_mode == "report_only")
    
    # Enterprise client allowed many more
    for _ in range(10):
        allowed, _, _ = await rl.check_rate_limit(client_ent, "Enterprise", "model")
        assert allowed is True
