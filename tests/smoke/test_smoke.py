from unittest.mock import AsyncMock, MagicMock

import pytest
from app.db.session import get_db, get_redis
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

# Helper for async mocks
async def mock_async_none(*args, **kwargs):
    return None

async def mock_async_val(val):
    return val

@pytest.fixture(autouse=True)
def setup_dependency_overrides():
    # Mock Redis
    mock_redis = MagicMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.incr = AsyncMock(return_value=1)
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.expire = AsyncMock(return_value=True)
    
    # Mock DB Session
    mock_db = MagicMock()
    mock_db.execute = AsyncMock(return_value=MagicMock())
    mock_db.commit = AsyncMock()
    mock_db.close = AsyncMock()
    
    app.dependency_overrides[get_redis] = lambda: mock_redis
    app.dependency_overrides[get_db] = lambda: mock_db
    
    yield
    
    app.dependency_overrides.clear()

def test_smoke_health_ready_models():
    # 1. Health
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    
    # 2. Ready
    response = client.get("/ready")
    assert response.status_code in [200, 503]
    
    # 3. Models (usually requires auth)
    response = client.get("/v1/models")
    assert response.status_code in [200, 401]

def test_smoke_admin_auth():
    response = client.get("/admin/operational-readiness")
    assert response.status_code in [401, 403, 404]

def test_smoke_client_chat_mock():
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": "Hello"}]
    }
    response = client.post("/v1/chat/completions", json=payload)
    assert response.status_code == 401

def test_smoke_billing_dry_run():
    response = client.get("/admin/billing/plans")
    assert response.status_code in [401, 403]

def test_smoke_rag_mock():
    response = client.get("/admin/rag/usage")
    assert response.status_code in [401, 403]

def test_smoke_metrics():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "llm_requests_total" in response.text
