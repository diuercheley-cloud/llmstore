import uuid

import pytest
from app.models.commercial.commercial_routing_event import CommercialRoutingEvent
from app.schemas.routing import TaskType
from app.services.routing import commercial_analytics
from sqlalchemy import select


@pytest.mark.asyncio
async def test_record_routing_event(session):
    client_id = uuid.uuid4()
    request_id = "test-req-1"
    
    event_id = await commercial_analytics.record_routing_event(
        session,
        client_id=client_id,
        request_id=request_id,
        endpoint="/v1/chat/completions",
        model_requested="gpt-4",
        task_type=TaskType.general,
        selected_provider="openai",
        selected_model="gpt-4o",
        estimated_cost_brl=0.05,
        estimated_revenue_brl=0.10,
        estimated_margin_brl=0.05,
        estimated_margin_percent=50.0,
    )
    
    assert event_id is not None
    await session.commit()
    
    # Verify persistence
    stmt = select(CommercialRoutingEvent).where(CommercialRoutingEvent.id == event_id)
    result = await session.execute(stmt)
    event = result.scalar_one()
    
    assert event.request_id == request_id
    assert event.selected_provider == "openai"
    assert event.estimated_margin_percent == 50.0
    assert event.actual_cost_brl is None

@pytest.mark.asyncio
async def test_update_actual_financials(session):
    request_id = "test-req-2"
    correlation_id = "test-corr-2"
    
    # Create initial event
    await commercial_analytics.record_routing_event(
        session,
        request_id=request_id,
        correlation_id=correlation_id,
        selected_provider="openai",
        estimated_cost_brl=0.05,
    )
    await session.commit()
    
    # Update actuals
    success = await commercial_analytics.update_actual_financials(
        session,
        request_id=request_id,
        actual_cost_brl=0.06,
        actual_revenue_brl=0.12,
        latency_ms=500
    )
    
    assert success is True
    await session.commit()
    
    # Verify update
    stmt = select(CommercialRoutingEvent).where(CommercialRoutingEvent.request_id == request_id)
    result = await session.execute(stmt)
    event = result.scalar_one()
    
    assert float(event.actual_cost_brl) == 0.06
    assert float(event.actual_revenue_brl) == 0.12
    assert float(event.actual_margin_brl) == 0.06
    assert float(event.actual_margin_percent) == 50.0
    assert event.latency_ms == 500

@pytest.mark.asyncio
async def test_summarize_today(session):
    # Clear existing events for today in this session if any (or just add new ones)
    await commercial_analytics.record_routing_event(
        session,
        selected_provider="openai",
        estimated_revenue_brl=10.0,
        estimated_cost_brl=5.0,
    )
    await commercial_analytics.record_routing_event(
        session,
        selected_provider="anthropic",
        estimated_revenue_brl=20.0,
        estimated_cost_brl=12.0,
        fallback_used=True
    )
    await session.commit()
    
    summary = await commercial_analytics.summarize_today(session)
    
    assert summary["events_today"] >= 2
    assert summary["fallback_count_today"] >= 1
    assert summary["estimated_revenue_today_brl"] >= 30.0
    assert "openai" in summary["selected_by_provider"]
    assert "anthropic" in summary["selected_by_provider"]

@pytest.mark.asyncio
async def test_sanitization(session):
    # Mock routes with some sensitive-looking data
    ranked_routes = [
        {"provider": "openai", "model": "gpt-4", "score": 0.9, "api_key": "secret-key", "prompt": "hidden"},
    ]
    
    event_id = await commercial_analytics.record_routing_event(
        session,
        ranked_routes=ranked_routes
    )
    await session.commit()
    
    stmt = select(CommercialRoutingEvent).where(CommercialRoutingEvent.id == event_id)
    result = await session.execute(stmt)
    event = result.scalar_one()
    
    # Check that api_key and prompt are NOT in the JSON
    routes_json = event.ranked_routes_json["routes"]
    assert len(routes_json) == 1
    assert "provider" in routes_json[0]
    assert "score" in routes_json[0]
    assert "api_key" not in routes_json[0]
    assert "prompt" not in routes_json[0]

@pytest.mark.asyncio
async def test_analytics_best_effort(session):
    # Test that it doesn't crash even with bad data (though record_routing_event catches all exceptions)
    # We pass None where it might expect something else
    event_id = await commercial_analytics.record_routing_event(
        session,
        client_id="not-a-uuid" # This might raise an error when adding to DB
    )
    
    # The service catches exceptions and returns None
    assert event_id is None
