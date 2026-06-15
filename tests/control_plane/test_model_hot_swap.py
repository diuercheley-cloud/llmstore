import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.core.config import get_settings
from app.core.time import utc_now
from app.models.operations.model_runtime import ModelRuntimeInstance
from app.services.model_runtime_manager import ModelRuntimeManager


@pytest.fixture
def mock_settings(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "model_hot_swap_enabled", True)
    monkeypatch.setattr(settings, "model_runtime_port_start", 18081)
    monkeypatch.setattr(settings, "model_runtime_port_end", 18085)
    return settings


class MockResult:
    def __init__(self, data):
        self.data = data

    def scalars(self):
        class MockScalars:
            def __init__(self, items):
                self.items = items

            def first(self):
                return self.items[0] if self.items else None

            def all(self):
                return self.items

        return MockScalars(self.data)


@pytest.mark.asyncio
async def test_load_model_gguf_validation(mock_settings):
    db = MagicMock()
    db.execute = AsyncMock(return_value=MockResult([]))
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    manager = ModelRuntimeManager(db)

    # Non-existent file
    with pytest.raises(ValueError, match="Model file not found"):
        await manager.load_model(uuid.uuid4(), uuid.uuid4(), "non_existent.gguf")

    # Invalid extension
    with patch("pathlib.Path.exists", return_value=True):
        with pytest.raises(ValueError, match="Only .gguf models are supported"):
            await manager.load_model(uuid.uuid4(), uuid.uuid4(), "model.bin")


@pytest.mark.asyncio
async def test_load_model_success(mock_settings):
    db = MagicMock()
    db.execute = AsyncMock(return_value=MockResult([]))
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    manager = ModelRuntimeManager(db)

    model_id = uuid.uuid4()
    backend_id = uuid.uuid4()

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.suffix", ".gguf"),
        patch("subprocess.Popen") as mock_popen,
    ):
        mock_popen.return_value = MagicMock()

        instance = await manager.load_model(model_id, backend_id, "test.gguf")

        assert instance.model_id == model_id
        assert instance.port == 18081
        assert instance.status == "loading"
        assert mock_popen.called


@pytest.mark.asyncio
async def test_activate_model(mock_settings):
    db = MagicMock()
    db.commit = AsyncMock()
    instance = ModelRuntimeInstance(
        id=uuid.uuid4(),
        model_id=uuid.uuid4(),
        backend_id=uuid.uuid4(),
        status="ready",
        is_active=False,
    )
    db.execute = AsyncMock(return_value=MockResult([instance]))
    manager = ModelRuntimeManager(db)

    await manager.activate_model(instance.id)
    assert instance.is_active is True
    assert db.execute.called


@pytest.mark.asyncio
async def test_rollback_model(mock_settings):
    db = MagicMock()
    db.commit = AsyncMock()
    mid = uuid.uuid4()
    bid = uuid.uuid4()

    old_instance = ModelRuntimeInstance(
        id=uuid.uuid4(),
        model_id=mid,
        backend_id=bid,
        status="ready",
        is_active=False,
        updated_at=utc_now(),
    )
    # Mocking rollback find: return old_instance
    # Mocking activate find: return old_instance
    db.execute = AsyncMock(
        side_effect=[
            MockResult([old_instance]),  # for rollback_active_model search
            MockResult([old_instance]),  # for activate_model find
            MockResult([]),  # for activate_model update
        ]
    )

    manager = ModelRuntimeManager(db)
    await manager.rollback_active_model(mid, bid)
    assert old_instance.is_active is True


@pytest.mark.asyncio
async def test_resolve_effective_backend_url(mock_settings):
    from app.models.core.model_backend_route import ModelBackendRoute
    from app.services.model_policy import resolve_effective_backend_url

    db = MagicMock()

    mid = uuid.uuid4()
    bid = uuid.uuid4()

    backend = MagicMock()
    backend.backend_url = "http://original:8081"

    route = ModelBackendRoute(model_registry_id=mid, inference_backend_id=bid)
    route.inference_backend = backend

    # Case 1: No active runtime
    db.execute = AsyncMock(return_value=MockResult([]))
    url = await resolve_effective_backend_url(db, route)
    assert url == "http://original:8081"

    # Case 2: With active runtime
    runtime = ModelRuntimeInstance(
        model_id=mid, backend_id=bid, port=18085, status="ready", is_active=True
    )
    db.execute = AsyncMock(return_value=MockResult([runtime]))

    url = await resolve_effective_backend_url(db, route)
    assert url == "http://localhost:18085"
