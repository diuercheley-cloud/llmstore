import os
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles


@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


TEST_TMP = Path("/tmp/llm-inference-stack-control-plane-tests")
TEST_TMP.mkdir(parents=True, exist_ok=True)
TEST_DB_FILE = TEST_TMP / "managed-control-plane.db"

os.environ.setdefault("ADMIN_TOKEN", "test-admin-token")
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{TEST_DB_FILE}")
os.environ.setdefault("REDIS_URL", "redis://test.invalid:6379/0")
os.environ.setdefault("DATA_PLANE_BASE_URL", "http://localhost:8081")
os.environ.setdefault("AGENT_EVENT_DRIVEN_ENABLED", "true")
os.environ.setdefault("AGENT_EVENT_HOOKS_ENABLED", "true")
os.environ.setdefault("AGENT_CRON_TRIGGERS_ENABLED", "true")
os.environ.setdefault("AGENT_PUBSUB_TRIGGERS_ENABLED", "true")
os.environ.setdefault("AGENT_EXTERNAL_WEBHOOK_TRIGGERS_ENABLED", "true")
os.environ.setdefault("AGENT_ASYNC_EXECUTION_ENABLED", "true")
os.environ.setdefault("AGENT_EXECUTION_PLANE_ENABLED", "true")
os.environ.setdefault("AGENT_RUNTIME_ENABLED", "true")
os.environ.setdefault("AGENT_IAM_ENABLED", "true")
os.environ.setdefault("AGENT_SERVICE_PRINCIPALS_ENABLED", "true")
os.environ.setdefault("AGENT_DELEGATED_TOKENS_ENABLED", "true")
os.environ.setdefault("AGENT_OAUTH_ON_BEHALF_OF_ENABLED", "true")
os.environ.setdefault("AGENT_AUTO_OPTIMIZATION_ENABLED", "true")
os.environ.setdefault("AGENT_DSPY_OPTIMIZER_ENABLED", "true")
os.environ.setdefault("AGENT_AUTO_PROMOTE_OPTIMIZATIONS", "true")
os.environ.setdefault("AGENT_OPTIMIZATION_APPLY_ENABLED", "true")
os.environ.setdefault("AGENT_MULTI_AGENT_ARBITRATION_ENABLED", "true")
os.environ.setdefault("AGENT_MULTI_AGENT_CRITIC_REVIEW_ENABLED", "true")
os.environ.setdefault("AGENT_MULTI_AGENT_MOCK_ARBITRATION", "true")




from app.core.config import get_settings
from app.main import app


@pytest_asyncio.fixture
async def async_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest.fixture
def admin_token_headers():
    settings = get_settings()
    token = settings.admin_super_token or settings.admin_token or "test-admin-token"
    return {"X-Admin-Token": token}


def pytest_collection_modifyitems(config, items):
    quick_files = {
        "test_intelligent_cache_exact.py",
        "test_commercial_qos_priority_queue.py",
        "test_queue_limits.py",
        "test_queue_priority.py",
        "test_tokenizer_service.py",
        "test_api_key_authentication.py",
        "test_alembic_heads.py",
        "test_check_secrets.py",
        "test_status_endpoints.py",
        "test_admin_readiness_security_sanitization.py",
        "test_admin_readiness_security_api.py",
        "test_admin_dashboard_readiness_security.py",
        "test_migrations_validation.py",
        "test_smoke.py",
        "test_crypto_trust_chain.py",
        "test_key_rotation.py",
        "test_policy_evaluator.py",
        "test_rego_runtime.py",
        "test_signing_service.py"
    }

    for item in items:
        path = str(item.fspath)
        filename = Path(path).name
        
        # All tests are included in release
        item.add_marker(pytest.mark.release)
        
        # 1. Chaos marker
        if "/chaos/" in path or "chaos" in item.name.lower():
            item.add_marker(pytest.mark.chaos)
        
        # 2. K8s marker
        elif "/kubernetes/" in path or "/k8s/" in path or "k8s" in item.name.lower():
            item.add_marker(pytest.mark.k8s)
            
        # 3. Quick marker
        elif filename in quick_files or "/smoke/" in path:
            item.add_marker(pytest.mark.quick)
            
        # 4. Slow marker
        else:
            item.add_marker(pytest.mark.slow)
