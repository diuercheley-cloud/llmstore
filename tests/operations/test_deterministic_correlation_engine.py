from datetime import datetime, timedelta

import pytest
from app.services.operations.correlation.deterministic_correlation_engine import (
    DeterministicOperationsCorrelationEngine,
)


@pytest.fixture
def engine():
    return DeterministicOperationsCorrelationEngine()

def test_correlate_empty_input(engine):
    result = engine.correlate([])
    assert result["correlation_type"] == "none"
    assert result["correlation_score"] == 0.0
    assert result["correlation_key"] == "empty"

def test_determinism(engine):
    events = [
        {"source_domain": "billing", "event_type": "overdue", "severity": "error", "timestamp": "2026-05-15T10:00:00Z"},
        {"source_domain": "runtime", "event_type": "latency_spike", "severity": "warning", "timestamp": "2026-05-15T10:01:00Z"}
    ]
    
    # Run multiple times with different input orders
    res1 = engine.correlate(events)
    res2 = engine.correlate(list(reversed(events)))
    
    assert res1 == res2
    assert res1["correlation_key"] == res2["correlation_key"]
    assert res1["correlation_score"] == res2["correlation_score"]

def test_score_increase_with_severity(engine):
    event_info = {"source_domain": "runtime", "event_type": "heartbeat", "severity": "info", "timestamp": "2026-05-15T10:00:00Z"}
    event_critical = {"source_domain": "runtime", "event_type": "crash", "severity": "critical", "timestamp": "2026-05-15T10:00:00Z"}
    
    res_low = engine.correlate([event_info])
    res_high = engine.correlate([event_critical])
    
    assert res_high["correlation_score"] > res_low["correlation_score"]

def test_cross_domain_bonus(engine):
    # Same domain
    events_single = [
        {"source_domain": "runtime", "event_type": "err1", "severity": "warning", "timestamp": "2026-05-15T10:00:00Z"},
        {"source_domain": "runtime", "event_type": "err2", "severity": "warning", "timestamp": "2026-05-15T10:00:10Z"}
    ]
    # Multiple domains
    events_multi = [
        {"source_domain": "runtime", "event_type": "err1", "severity": "warning", "timestamp": "2026-05-15T10:00:00Z"},
        {"source_domain": "billing", "event_type": "err2", "severity": "warning", "timestamp": "2026-05-15T10:00:10Z"}
    ]
    
    res_single = engine.correlate(events_single)
    res_multi = engine.correlate(events_multi)
    
    assert res_multi["correlation_score"] > res_single["correlation_score"]
    assert res_multi["correlation_type"] == "cross_domain_impact"

def test_temporal_proximity(engine):
    base_ts = datetime(2026, 5, 15, 12, 0, 0)
    
    # Very close events
    close_events = [
        {"source_domain": "a", "event_type": "e1", "severity": "info", "timestamp": base_ts.isoformat()},
        {"source_domain": "b", "event_type": "e2", "severity": "info", "timestamp": (base_ts + timedelta(seconds=10)).isoformat()}
    ]
    # Far apart events
    far_events = [
        {"source_domain": "a", "event_type": "e1", "severity": "info", "timestamp": base_ts.isoformat()},
        {"source_domain": "b", "event_type": "e2", "severity": "info", "timestamp": (base_ts + timedelta(minutes=50)).isoformat()}
    ]
    
    res_close = engine.correlate(close_events)
    res_far = engine.correlate(far_events)
    
    assert res_close["correlation_score"] > res_far["correlation_score"]

def test_forecast_alignment(engine):
    events = [{"source_domain": "runtime", "event_type": "e1", "severity": "warning", "timestamp": "2026-05-15T10:00:00Z"}]
    forecasts = [{"target_domain": "runtime", "risk_score": 0.9}]
    
    res_no_forecast = engine.correlate(events)
    res_with_forecast = engine.correlate(events, forecasts=forecasts)
    
    assert res_with_forecast["correlation_score"] > res_no_forecast["correlation_score"]

def test_explanation_generation(engine):
    events = [
        {"source_domain": "billing", "event_type": "fail", "severity": "critical", "timestamp": "2026-05-15T10:00:00Z"},
        {"source_domain": "runtime", "event_type": "fail", "severity": "critical", "timestamp": "2026-05-15T10:00:01Z"}
    ]
    result = engine.correlate(events)
    
    assert "cross_domain_impact" in result["explanation"]
    assert "billing" in result["explanation"]
    assert "runtime" in result["explanation"]
    assert result["advisory_only"] is True
