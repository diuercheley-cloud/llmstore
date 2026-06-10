from datetime import datetime, timedelta, timezone

import pytest
from app.services.routing.commercial_live_balancer import CommercialLiveBalancer


@pytest.fixture
def balancer():
    return CommercialLiveBalancer()

def test_apply_hysteresis(balancer):
    balancer.settings.commercial_live_balancing_hysteresis_percent = 10.0
    
    # Change is 5%, which is less than 10% hysteresis
    assert balancer.apply_hysteresis(50.0, 55.0) == 50.0
    
    # Change is 15%, which is more than 10% hysteresis
    assert balancer.apply_hysteresis(50.0, 65.0) == 65.0

def test_calculate_balancing_delta(balancer):
    balancer.settings.commercial_live_balancing_max_traffic_change_percent = 5.0
    
    # Diff is 20%, but max change is 5%
    assert balancer.calculate_balancing_delta(50.0, 70.0) == 5.0
    assert balancer.calculate_balancing_delta(50.0, 30.0) == -5.0
    
    # Diff is 2%, within max change
    assert balancer.calculate_balancing_delta(50.0, 52.0) == 2.0

def test_detect_flapping(balancer):
    balancer.settings.commercial_live_balancing_min_stable_minutes = 30
    cluster_id = "test-cluster"
    
    now = datetime.now(timezone.utc)
    history = [
        {"cluster_id": cluster_id, "timestamp": now - timedelta(minutes=10), "change_percent": 5.0}
    ]
    
    # Too soon (10 mins < 30 mins)
    assert balancer.detect_flapping(cluster_id, 5.0, history) is True
    
    # Different direction also counts as flapping/oscillation
    history2 = [
        {"cluster_id": cluster_id, "timestamp": now - timedelta(minutes=40), "change_percent": 5.0}
    ]
    assert balancer.detect_flapping(cluster_id, -5.0, history2) is True # Changed direction
    
    # OK case
    assert balancer.detect_flapping(cluster_id, 5.0, history2) is False

def test_recommend_rebalance(balancer):
    balancer.settings.commercial_live_balancing_enabled = True
    balancer.settings.commercial_live_balancing_min_margin_percent = 20.0
    
    metrics = {"margin_percent": 15.0}
    recommendation = balancer.recommend_rebalance("c1", metrics, [])
    
    assert recommendation["action"] == "decrease"
    assert recommendation["reason"] == "low_margin"
