import pytest

from app.services.circuit_breaker import CircuitBreaker, CircuitBreakerOpen


@pytest.mark.asyncio
async def test_circuit_breaker_reset_clears_open_state():
    breaker = CircuitBreaker()
    breaker.failure_threshold = 1
    breaker.recovery_seconds = 60

    await breaker.record_failure()

    with pytest.raises(CircuitBreakerOpen):
        await breaker.before_call()

    await breaker.reset()
    await breaker.before_call()

    assert breaker.failures == 0
    assert breaker.opened_at == 0.0
