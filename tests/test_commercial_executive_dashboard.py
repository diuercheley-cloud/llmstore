import uuid
from datetime import datetime, timedelta, timezone

import pytest
from app.models.commercial_routing_event import CommercialRoutingEvent
from app.services.routing.commercial_executive_dashboard import CommercialExecutiveDashboardService


@pytest.mark.asyncio
async def test_executive_overview_empty(session):
    service = CommercialExecutiveDashboardService(session)
    overview = await service.get_overview(hours=24)
    
    assert "profitability" in overview
    assert "drift" in overview
    assert overview["profitability"]["total_requests"] == 0
    assert overview["profitability"]["actual_revenue_brl"] == 0
    assert overview["drift"]["cost_drift_percent"] == 0

@pytest.mark.asyncio
async def test_executive_overview_populated(session):
    service = CommercialExecutiveDashboardService(session)
    
    # Add some events for the current period (last 24h)
    now = datetime.now(timezone.utc)
    
    # Event 1: Profitable
    session.add(CommercialRoutingEvent(
        actual_revenue_brl=1.0,
        actual_cost_brl=0.5,
        actual_margin_brl=0.5,
        actual_margin_percent=50.0,
        estimated_revenue_brl=1.0,
        estimated_cost_brl=0.5,
        latency_ms=200,
        created_at=now - timedelta(hours=2)
    ))
    
    # Event 2: Loss
    session.add(CommercialRoutingEvent(
        actual_revenue_brl=1.0,
        actual_cost_brl=1.5,
        actual_margin_brl=-0.5,
        actual_margin_percent=-50.0,
        estimated_revenue_brl=1.0,
        estimated_cost_brl=0.5, # Error in estimation
        latency_ms=800,
        created_at=now - timedelta(hours=1)
    ))
    
    await session.commit()
    
    overview = await service.get_overview(hours=24)
    
    assert overview["profitability"]["total_requests"] >= 2
    assert overview["profitability"]["actual_revenue_brl"] == 2.0
    assert overview["profitability"]["actual_cost_brl"] == 2.0
    assert overview["profitability"]["actual_margin_brl"] == 0.0
    assert overview["profitability"]["estimation_error_percent"] > 0
    
    # Check anomalies
    anomalies = overview["anomalies"]
    types = [a["type"] for a in anomalies]
    assert "negative_margin" in types

@pytest.mark.asyncio
async def test_drift_calculation(session):
    service = CommercialExecutiveDashboardService(session)
    now = datetime.now(timezone.utc)
    
    # Previous period (24h to 48h ago): Low cost
    session.add(CommercialRoutingEvent(
        actual_cost_brl=0.10,
        actual_margin_percent=50.0,
        latency_ms=100,
        created_at=now - timedelta(hours=30)
    ))
    
    # Current period (0h to 24h ago): High cost
    session.add(CommercialRoutingEvent(
        actual_cost_brl=0.20,
        actual_margin_percent=25.0,
        latency_ms=300,
        created_at=now - timedelta(hours=5)
    ))
    
    await session.commit()
    
    drift = await service.get_drift_overview(since=now - timedelta(hours=24))
    
    # Cost doubled (+100%)
    assert drift["cost_drift_percent"] == 100.0
    # Latency tripled (+200%)
    assert drift["latency_drift_percent"] == 200.0
    # Margin halved (-50%)
    assert drift["margin_drift_percent"] == -50.0

@pytest.mark.asyncio
async def test_executive_recommendations(session):
    service = CommercialExecutiveDashboardService(session)
    
    anomalies = [
        {"type": "negative_margin", "message": "Detected negative margin"},
        {"type": "cost_drift", "message": "High cost drift"}
    ]
    canaries = {"active_canaries_count": 0, "pass_rate_percent": 100, "auto_rollback_count_24h": 1}
    
    recs = await service.generate_executive_recommendations(anomalies, canaries)
    
    titles = [r["title"] for r in recs]
    assert "Review Pricing or Policies" in titles
    assert "Recalibrate Provider Costs" in titles
    assert "Audit Auto-Rollbacks" in titles

@pytest.mark.asyncio
async def test_client_provider_summaries(session):
    service = CommercialExecutiveDashboardService(session)
    now = datetime.now(timezone.utc)
    client_id = uuid.uuid4()
    
    session.add(CommercialRoutingEvent(
        client_id=client_id,
        selected_provider="provider-a",
        actual_revenue_brl=10.0,
        actual_cost_brl=2.0,
        actual_margin_brl=8.0,
        actual_margin_percent=80.0,
        created_at=now - timedelta(hours=1)
    ))
    
    await session.commit()
    
    clients = await service.summarize_clients_profitability(since=now - timedelta(hours=24))
    providers = await service.summarize_providers_profitability(since=now - timedelta(hours=24))
    
    assert len(clients) > 0
    assert clients[0]["client_id"] == str(client_id)
    assert clients[0]["margin_brl"] == 8.0
    
    assert len(providers) > 0
    assert providers[0]["provider"] == "provider-a"
    assert providers[0]["margin_brl"] == 8.0
