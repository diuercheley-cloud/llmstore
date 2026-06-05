import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.inference.router import InferenceRouter
from app.services.inference.backends.base import Capability
from app.services.inference.backends.vllm_backend import VLLMBackend
from app.services.inference.backends.tgi_backend import TGIBackend
from app.models.inference_backend import InferenceBackend
from app.services.runtime.hardware_detection import HardwareSpecs


@pytest.fixture
def mock_session():
    session = AsyncMock()
    return session


@pytest.fixture
def mock_backends():
    b1 = InferenceBackend(
        name="vllm-primary", 
        provider="vllm", 
        backend_url="http://vllm:8000",
        is_active=True
    )
    b2 = InferenceBackend(
        name="tgi-secondary", 
        provider="tgi", 
        backend_url="http://tgi:8080",
        is_active=True
    )
    return [b1, b2]


@pytest.mark.asyncio
async def test_router_selects_highest_priority(mock_session, mock_backends):
    # Setup mock result
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = mock_backends
    mock_session.execute.return_value = mock_result

    router = InferenceRouter(mock_session)
    
    # Test chat capability (vLLM should be preferred over TGI)
    adapter, reason = await router.get_best_backend("gpt-4", Capability.CHAT)
    
    assert adapter is not None
    assert isinstance(adapter, VLLMBackend)
    assert adapter.name == "vllm-primary"
    assert "priority" in reason.lower()


@pytest.mark.asyncio
async def test_router_fallback_when_vllm_inactive(mock_session, mock_backends):
    # Make vLLM inactive
    mock_backends[0].is_active = False
    
    # Filter only active
    active_backends = [b for b in mock_backends if b.is_active]
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = active_backends
    mock_session.execute.return_value = mock_result

    router = InferenceRouter(mock_session)
    
    adapter, reason = await router.get_best_backend("gpt-4", Capability.CHAT)
    
    assert adapter is not None
    assert isinstance(adapter, TGIBackend)
    assert adapter.name == "tgi-secondary"


@pytest.mark.asyncio
async def test_hardware_detection_mock():
    with patch("subprocess.run") as mock_run:
        # Mock nvidia-smi output
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "NVIDIA GeForce RTX 3090, 24576\n"
        
        from app.services.runtime.hardware_detection import detect_hardware
        specs = detect_hardware()
        
        assert specs.gpu_count == 1
        assert "3090" in specs.gpu_type
        assert specs.vram_total_gb == 24.0
        assert specs.cuda_available is True


@pytest.mark.asyncio
async def test_router_no_backends_found(mock_session):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    router = InferenceRouter(mock_session)
    adapter, reason = await router.get_best_backend("gpt-4", Capability.CHAT)
    
    assert adapter is None
    assert "no active backends" in reason.lower()


@pytest.mark.asyncio
async def test_admin_api_list_backends(mock_session, mock_backends):
    # Mocking the session.execute for the API endpoint
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = mock_backends
    mock_session.execute.return_value = mock_result
    
    from app.api.admin_inference import list_inference_backends
    
    # Mock health checks to avoid real HTTP calls
    with patch.object(VLLMBackend, "health", return_value=True), \
         patch.object(TGIBackend, "health", return_value=True):
        
        response = await list_inference_backends(mock_session)
        
        assert len(response) == 2
        assert response[0]["name"] == "vllm-primary"
        assert response[0]["health"] == "healthy"
        assert "chat" in response[0]["capabilities"]
