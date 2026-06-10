from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from app.models.commercial.commercial_cluster_registry import CommercialClusterRegistry
from app.services.routing.commercial_cross_cluster_forwarder import (
    CommercialCrossClusterForwarder,
    _circuit_breakers,
)
from httpx import Response


@pytest_asyncio.fixture(autouse=True)
def override_config():
    with patch("app.services.routing.commercial_cross_cluster_forwarder.cfg") as mock_cfg:
        mock_cfg.commercial_cross_cluster_forwarding_enabled = True
        mock_cfg.commercial_cross_cluster_forwarding_mode = "forwarding"
        mock_cfg.commercial_cross_cluster_forwarding_circuit_breaker_enabled = True
        mock_cfg.commercial_cross_cluster_forwarding_circuit_breaker_failure_threshold = 2
        mock_cfg.commercial_cross_cluster_forwarding_circuit_breaker_reset_seconds = 1
        mock_cfg.commercial_cross_cluster_forwarding_timeout_seconds = 2
        mock_cfg.commercial_cross_cluster_forwarding_require_jwt = True
        mock_cfg.secret_key = "test"
        
        # Clear circuit breakers
        _circuit_breakers.clear()
        
        yield mock_cfg

@pytest.fixture
def mock_session():
    session = AsyncMock()
    return session

@pytest.fixture
def mock_target_cluster():
    cluster = CommercialClusterRegistry(
        cluster_id="target-1",
        name="Target 1",
        status="active",
        forwarding_enabled=True,
        forwarding_status="healthy",
        forwarding_base_url="http://target-1:8000"
    )
    return cluster

@pytest.mark.asyncio
async def test_should_forward_request(mock_session, mock_target_cluster):
    forwarder = CommercialCrossClusterForwarder(mock_session)
    assert forwarder.should_forward_request(mock_target_cluster) == True
    
    # disable feature
    with patch("app.services.routing.commercial_cross_cluster_forwarder.cfg") as mock_cfg:
        mock_cfg.commercial_cross_cluster_forwarding_enabled = False
        assert forwarder.should_forward_request(mock_target_cluster) == False

@pytest.mark.asyncio
async def test_circuit_breaker(mock_session, mock_target_cluster):
    forwarder = CommercialCrossClusterForwarder(mock_session)
    
    forwarder.mark_failure("target-1")
    assert forwarder.is_circuit_open("target-1") == False # threshold is 2
    
    forwarder.mark_failure("target-1")
    assert forwarder.is_circuit_open("target-1") == True # threshold reached
    assert forwarder.should_forward_request(mock_target_cluster) == False
    
    # mark success shouldn't do anything directly if it's already open, but let's test it closes
    forwarder.mark_success("target-1")
    assert forwarder.is_circuit_open("target-1") == False

@pytest.mark.asyncio
async def test_forward_request_success(mock_session, mock_target_cluster):
    forwarder = CommercialCrossClusterForwarder(mock_session)
    
    request = MagicMock()
    request.method = "POST"
    request.url.path = "/v1/chat/completions"
    request.headers = {"Authorization": "Bearer fake", "content-type": "application/json"}
    
    body = b'{"model":"fake"}'
    
    mock_resp = Response(200, content=b'{"id":"1"}')
    
    with patch("httpx.AsyncClient.request", return_value=mock_resp):
        response = await forwarder.forward_request(request, mock_target_cluster, body)
        assert response is not None
        assert response.status_code == 200
        # DB add event should be called
        assert mock_session.add.called
        
@pytest.mark.asyncio
async def test_forward_request_fallback_on_error(mock_session, mock_target_cluster):
    forwarder = CommercialCrossClusterForwarder(mock_session)
    
    request = MagicMock()
    request.method = "POST"
    request.url.path = "/v1/chat/completions"
    request.headers = {}
    
    body = b'{}'
    
    # Simulate timeout or error
    with patch("httpx.AsyncClient.request", side_effect=Exception("Timeout")):
        response = await forwarder.forward_request(request, mock_target_cluster, body)
        assert response is None # Fallback local
        assert forwarder.is_circuit_open("target-1") == False # Only 1 failure
        
        # Second failure should open circuit
        await forwarder.forward_request(request, mock_target_cluster, body)
        assert forwarder.is_circuit_open("target-1") == True
