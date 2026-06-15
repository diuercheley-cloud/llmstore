from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from app.contracts.backend_lifecycle import (
    BackendLifecycleCapabilities,
    BackendObservedState,
    LifecycleActionResult,
)
from app.services.backend_lifecycle.manager import BackendLifecycleManager
from app.services.backend_lifecycle.providers import ProviderUnavailableError


def _make_caps(
    can_start=True, can_stop=True, can_restart=True, can_observe=True, provider_type="test"
):
    return BackendLifecycleCapabilities(
        can_start=can_start,
        can_stop=can_stop,
        can_restart=can_restart,
        can_observe=can_observe,
        provider_type=provider_type,
    )


def _backend_mock(
    backend_id=None,
    name="test-backend",
    provider="llama.cpp",
    url="http://localhost:8080",
    is_active=True,
    status="running",
    metadata_json=None,
    updated_at=None,
):
    b = Mock()
    b.id = backend_id or uuid4()
    b.name = name
    b.provider = provider
    b.backend_url = url
    b.is_active = is_active
    b.status = status
    b.metadata_json = metadata_json
    b.updated_at = updated_at
    return b


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.get.return_value = _backend_mock()
    return db


@pytest.fixture
def mock_provider():
    provider = Mock()
    provider.capabilities = Mock(return_value=_make_caps())
    provider.get_observed_state = AsyncMock(
        return_value=BackendObservedState(
            backend_id=uuid4(),
            provider="test",
            running=True,
            healthy=True,
        )
    )
    provider.start_backend = AsyncMock(
        return_value=LifecycleActionResult(
            success=True,
            action="start",
            backend_id=uuid4(),
            message="started",
        )
    )
    provider.stop_backend = AsyncMock(
        return_value=LifecycleActionResult(
            success=True,
            action="stop",
            backend_id=uuid4(),
            message="stopped",
        )
    )
    provider.restart_backend = AsyncMock(
        return_value=LifecycleActionResult(
            success=True,
            action="restart",
            backend_id=uuid4(),
            message="restarted",
        )
    )
    return provider


@pytest.mark.asyncio
async def test_manager_capabilities(mock_db, mock_provider):
    manager = BackendLifecycleManager(db=mock_db, provider=mock_provider)
    caps = manager.capabilities()
    assert caps.can_start is True
    assert caps.can_stop is True


@pytest.mark.asyncio
async def test_manager_get_desired_state(mock_db, mock_provider):
    manager = BackendLifecycleManager(db=mock_db, provider=mock_provider)
    desired = await manager.get_desired_state(uuid4())
    assert desired is not None
    assert desired.name == "test-backend"


@pytest.mark.asyncio
async def test_manager_get_desired_state_not_found(mock_db, mock_provider):
    mock_db.get.return_value = None
    manager = BackendLifecycleManager(db=mock_db, provider=mock_provider)
    desired = await manager.get_desired_state(uuid4())
    assert desired is None


@pytest.mark.asyncio
async def test_manager_get_observed_state(mock_db, mock_provider):
    manager = BackendLifecycleManager(db=mock_db, provider=mock_provider)
    observed = await manager.get_observed_state(uuid4())
    assert observed.running is True
    assert observed.healthy is True


@pytest.mark.asyncio
async def test_manager_start_backend(mock_db, mock_provider):
    manager = BackendLifecycleManager(db=mock_db, provider=mock_provider)
    result = await manager.start_backend(uuid4())
    assert result.success is True
    assert result.action == "start"


@pytest.mark.asyncio
async def test_manager_stop_backend(mock_db, mock_provider):
    manager = BackendLifecycleManager(db=mock_db, provider=mock_provider)
    result = await manager.stop_backend(uuid4())
    assert result.success is True
    assert result.action == "stop"


@pytest.mark.asyncio
async def test_manager_restart_backend(mock_db, mock_provider):
    manager = BackendLifecycleManager(db=mock_db, provider=mock_provider)
    result = await manager.restart_backend(uuid4())
    assert result.success is True
    assert result.action == "restart"


@pytest.mark.asyncio
async def test_manager_start_backend_not_found(mock_db, mock_provider):
    mock_db.get.return_value = None
    manager = BackendLifecycleManager(db=mock_db, provider=mock_provider)
    result = await manager.start_backend(uuid4())
    assert result.success is False
    assert "not found" in result.message


@pytest.mark.asyncio
async def test_manager_stop_backend_not_found(mock_db, mock_provider):
    mock_db.get.return_value = None
    manager = BackendLifecycleManager(db=mock_db, provider=mock_provider)
    result = await manager.stop_backend(uuid4())
    assert result.success is False
    assert "not found" in result.message


@pytest.mark.asyncio
async def test_manager_reconcile_one(mock_db, mock_provider):
    backend_id = uuid4()
    mock_db.get.return_value = _backend_mock(backend_id=backend_id)
    manager = BackendLifecycleManager(db=mock_db, provider=mock_provider)
    result = await manager.reconcile_one(backend_id)
    assert "desired" in result
    assert "observed" in result
    assert "drifts" in result


@pytest.mark.asyncio
async def test_manager_reconcile_one_not_found(mock_db, mock_provider):
    mock_db.get.return_value = None
    manager = BackendLifecycleManager(db=mock_db, provider=mock_provider)
    result = await manager.reconcile_one(uuid4())
    assert "error" in result


@pytest.mark.asyncio
async def test_manager_drift_history(mock_db, mock_provider):
    manager = BackendLifecycleManager(db=mock_db, provider=mock_provider)
    history = manager.drift_history()
    assert history == []


@pytest.mark.asyncio
async def test_manager_provider_unavailable_error(mock_db):
    provider = Mock()
    provider.capabilities = Mock(
        return_value=_make_caps(
            can_start=False,
            can_stop=False,
            can_restart=False,
            can_observe=True,
            provider_type="disabled",
        )
    )
    mock_db.get.return_value = _backend_mock()
    manager = BackendLifecycleManager(db=mock_db, provider=provider)
    with pytest.raises(ProviderUnavailableError):
        await manager.start_backend(uuid4())


@pytest.mark.asyncio
async def test_manager_reconcile_all(mock_db, mock_provider):

    result_mock = Mock()
    result_mock.scalars.return_value.all.return_value = [
        _backend_mock(name="a"),
        _backend_mock(name="b"),
    ]
    mock_db.execute = AsyncMock(return_value=result_mock)
    manager = BackendLifecycleManager(db=mock_db, provider=mock_provider)
    results = await manager.reconcile_all()
    assert len(results) == 2
