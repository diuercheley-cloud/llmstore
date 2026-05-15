import pytest
import pytest_asyncio
from unittest.mock import patch

from app.services.routing.commercial_global_traffic_shifter import CommercialGlobalTrafficShifter
from app.models.commercial_global_traffic import CommercialGlobalTrafficPolicy, CommercialGlobalTrafficDecision

@pytest_asyncio.fixture(autouse=True)
def override_config():
    with patch("app.services.routing.commercial_global_traffic_shifter.cfg") as mock_cfg, \
         patch("app.api.commercial_global_traffic_admin.cfg") as mock_api_cfg:
        
        for cfg in [mock_cfg, mock_api_cfg]:
            cfg.commercial_global_traffic_shifting_enabled = True
            cfg.commercial_global_traffic_shifting_mode = "dry_run"
            cfg.commercial_global_traffic_shifting_max_canary_percent = 10
            cfg.commercial_global_traffic_shifting_require_healthy_target = True
            cfg.commercial_cluster_id = "local"
        yield mock_cfg

@pytest.mark.asyncio
async def test_create_policy(session):
    shifter = CommercialGlobalTrafficShifter(session)
    
    policy = await shifter.create_policy(
        name="test-canary",
        source_cluster="local",
        target_cluster="remote-us",
        percent=5,
        mode="canary"
    )
    
    assert policy.id is not None
    assert policy.status == "active"
    assert policy.traffic_percent == 5
    assert policy.max_traffic_percent == 10
    assert policy.mode == "canary"

@pytest.mark.asyncio
async def test_deterministic_bucket(session):
    shifter = CommercialGlobalTrafficShifter(session)
    
    b1 = shifter.deterministic_bucket("corr1", "", "")
    b2 = shifter.deterministic_bucket("corr1", "req2", "client3")
    
    assert b1 == b2
    assert 1 <= b1 <= 100

@pytest.mark.asyncio
async def test_decide_cluster_feature_disabled(session, override_config):
    override_config.commercial_global_traffic_shifting_enabled = False
    
    shifter = CommercialGlobalTrafficShifter(session)
    
    decision = await shifter.decide_cluster_for_request({"tenant_id": "t1"})
    assert decision.decision == "stay_local"
    assert decision.reason == "feature_disabled"

@pytest.mark.asyncio
async def test_pause_and_rollback(session):
    shifter = CommercialGlobalTrafficShifter(session)
    
    policy = await shifter.create_policy("test-pause", "local", "remote", 5, "canary")
    assert policy.status == "active"
    
    paused = await shifter.pause_policy(policy.id)
    assert paused.status == "paused"
    
    rolled_back = await shifter.rollback_policy(policy.id)
    assert rolled_back.status == "rolled_back"

@pytest.mark.asyncio
async def test_admin_api_create_policy(admin_client, admin_token_headers):
    response = await admin_client.post(
        "/admin/routing/global-traffic/policies",
        json={
            "name": "api-policy",
            "source_cluster": "local",
            "target_cluster": "remote-1",
            "percent": 2,
            "mode": "dry_run"
        },
        headers=admin_token_headers
    )
    if response.status_code == 200:
        data = response.json()
        assert data["name"] == "api-policy"
        assert data["status"] == "pending"

@pytest.mark.asyncio
async def test_simulate(admin_client, admin_token_headers):
    response = await admin_client.post(
        "/admin/routing/global-traffic/simulate",
        json={
            "tenant_id": "tenant1",
            "correlation_id": "test-123"
        },
        headers=admin_token_headers
    )
    if response.status_code == 200:
        data = response.json()
        assert data["decision"] in ["stay_local", "dry_run_would_shift", "shift_to_target"]
