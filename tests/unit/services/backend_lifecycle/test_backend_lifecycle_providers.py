from uuid import uuid4

import pytest

from app.contracts.backend_lifecycle import BackendDesiredState
from app.services.backend_lifecycle.providers import (
    DockerProvider,
    KubernetesProvider,
    LocalProcessProvider,
    ProviderUnavailableError,
)


@pytest.fixture
def desired_state():
    return BackendDesiredState(
        backend_id=uuid4(),
        name="test-backend",
        provider="llama.cpp",
        backend_url="http://localhost:8080",
        is_active=True,
        status="running",
    )


@pytest.mark.asyncio
async def test_local_process_provider_observed_state_not_running(desired_state):
    provider = LocalProcessProvider()
    observed = await provider.get_observed_state(desired_state.backend_id, desired_state)
    assert observed.running is False
    assert observed.healthy is False
    assert observed.error is not None
    assert "no local process" in observed.error


@pytest.mark.asyncio
async def test_local_process_provider_capabilities():
    provider = LocalProcessProvider()
    caps = provider.capabilities()
    assert caps.can_start is True
    assert caps.can_stop is True
    assert caps.can_restart is True
    assert caps.provider_type == "local_process"


@pytest.mark.asyncio
async def test_local_process_provider_stop_without_start(desired_state):
    provider = LocalProcessProvider()
    result = await provider.stop_backend(desired_state.backend_id, desired_state)
    assert result.success is True
    assert "no running process" in result.message


@pytest.mark.asyncio
async def test_docker_provider_capabilities():
    provider = DockerProvider()
    caps = provider.capabilities()
    assert caps.can_start is True
    assert caps.can_stop is True
    assert caps.can_restart is True
    assert caps.provider_type == "docker"


@pytest.mark.asyncio
async def test_docker_provider_observed_not_allowed(desired_state):
    provider = DockerProvider()
    observed = await provider.get_observed_state(desired_state.backend_id, desired_state)
    assert observed.running is False
    assert observed.healthy is False


@pytest.mark.asyncio
async def test_kubernetes_provider_capabilities():
    provider = KubernetesProvider()
    caps = provider.capabilities()
    assert caps.provider_type == "kubernetes_unavailable"
    assert caps.can_start is False
    assert caps.can_observe is False


@pytest.mark.asyncio
async def test_kubernetes_provider_observed_unavailable(desired_state):
    provider = KubernetesProvider()
    observed = await provider.get_observed_state(desired_state.backend_id, desired_state)
    assert observed.running is False
    assert "unavailable" in (observed.error or "")


@pytest.mark.asyncio
async def test_kubernetes_provider_start_raises(desired_state):
    provider = KubernetesProvider()
    with pytest.raises(ProviderUnavailableError):
        await provider.start_backend(desired_state.backend_id, desired_state)


@pytest.mark.asyncio
async def test_local_process_start_fails_no_binary(desired_state):
    provider = LocalProcessProvider()
    result = await provider.start_backend(desired_state.backend_id, desired_state)
    assert result.success is False
