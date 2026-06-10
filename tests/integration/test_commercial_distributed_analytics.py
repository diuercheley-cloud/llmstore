from __future__ import annotations

from datetime import timedelta

import pytest
from app.core.config import get_settings
from app.core.time import utc_now
from app.models.commercial.commercial_cluster_aggregate import CommercialClusterAggregate
from app.models.commercial.commercial_node_heartbeat import CommercialNodeHeartbeat
from app.models.commercial.commercial_routing_event import CommercialRoutingEvent
from app.models.commercial.commercial_routing_event_ingest import CommercialRoutingEventIngest
from app.services.routing import commercial_analytics
from app.services.routing.commercial_cluster_aggregates import (
    aggregate_bucket,
    cleanup_old_analytics,
    get_cluster_overview,
)
from app.services.routing.commercial_event_ingest import (
    ingest_routing_event,
    process_pending_events,
)
from app.services.routing.commercial_node_heartbeat import (
    list_nodes,
    mark_stale_nodes_offline,
    resolve_node_identity,
    summarize_cluster_health,
    write_heartbeat,
)
from sqlalchemy import select


def _enable_distributed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMMERCIAL_DISTRIBUTED_ANALYTICS_ENABLED", "true")
    monkeypatch.setenv("NODE_ID", "node-test-1")
    monkeypatch.setenv("NODE_ROLE", "api")
    monkeypatch.setenv("CLUSTER_ID", "cluster-test")
    monkeypatch.setenv("COMMERCIAL_NODE_OFFLINE_AFTER_SECONDS", "1")
    monkeypatch.setenv("COMMERCIAL_NODE_HEARTBEAT_INTERVAL_SECONDS", "1")
    monkeypatch.setenv("COMMERCIAL_ANALYTICS_RETENTION_DAYS", "30")
    monkeypatch.setenv("COMMERCIAL_ANALYTICS_AGGREGATION_BUCKET_MINUTES", "5")
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_heartbeat_creates_and_updates_node(session, monkeypatch):
    _enable_distributed(monkeypatch)
    identity = resolve_node_identity()
    first = await write_heartbeat(session, identity)
    await session.commit()
    second = await write_heartbeat(session, identity)
    await session.commit()

    assert first["node_id"] == "node-test-1"
    assert second["status"] == "healthy"
    rows = (await session.execute(select(CommercialNodeHeartbeat))).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_stale_node_becomes_offline(session, monkeypatch):
    _enable_distributed(monkeypatch)
    heartbeat = CommercialNodeHeartbeat(
        node_id="node-old",
        node_role="worker",
        hostname="old-host",
        started_at=utc_now() - timedelta(minutes=10),
        last_seen_at=utc_now() - timedelta(minutes=10),
        status="healthy",
        metadata_json={},
    )
    session.add(heartbeat)
    await session.flush()

    changed = await mark_stale_nodes_offline(session)
    await session.commit()
    nodes = await list_nodes(session)

    assert changed == 1
    assert nodes[0]["status"] == "offline"


@pytest.mark.asyncio
async def test_ingest_event_new(session, monkeypatch):
    _enable_distributed(monkeypatch)
    result = await ingest_routing_event(
        session,
        {
            "request_id": "req-1",
            "correlation_id": "corr-1",
            "selected_provider": "openai",
        },
        "node-a",
    )
    await session.commit()

    assert result["accepted"] is True
    row = (await session.execute(select(CommercialRoutingEventIngest))).scalars().one()
    assert row.status == "pending"
    assert row.node_id == "node-a"


@pytest.mark.asyncio
async def test_ingest_duplicate_becomes_duplicate(session, monkeypatch):
    _enable_distributed(monkeypatch)
    payload = {"request_id": "req-dup", "correlation_id": "corr-dup", "selected_provider": "openai"}
    first = await ingest_routing_event(session, payload, "node-a")
    second = await ingest_routing_event(session, payload, "node-b")
    await session.commit()

    rows = (await session.execute(select(CommercialRoutingEventIngest).order_by(CommercialRoutingEventIngest.received_at.asc()))).scalars().all()
    assert first["status"] == "pending"
    assert second["status"] == "duplicate"
    assert rows[1].status == "duplicate"


@pytest.mark.asyncio
async def test_process_pending_creates_main_event(session, monkeypatch):
    _enable_distributed(monkeypatch)
    await ingest_routing_event(
        session,
        {
            "request_id": "req-process",
            "correlation_id": "corr-process",
            "endpoint": "/v1/chat/completions",
            "model_requested": "gpt-test",
            "selected_provider": "openai",
            "selected_model": "gpt-4o-mini",
            "estimated_revenue_brl": 2.5,
            "estimated_cost_brl": 1.0,
            "estimated_margin_brl": 1.5,
        },
        "node-a",
    )

    summary = await process_pending_events(session)
    await session.commit()

    event = (await session.execute(select(CommercialRoutingEvent))).scalars().one()
    ingest = (await session.execute(select(CommercialRoutingEventIngest))).scalars().one()
    assert summary["processed"] == 1
    assert event.request_id == "req-process"
    assert ingest.status == "processed"


@pytest.mark.asyncio
async def test_aggregate_bucket(session, monkeypatch):
    _enable_distributed(monkeypatch)
    await commercial_analytics.record_routing_event(
        session,
        request_id="req-agg",
        correlation_id="corr-agg",
        model_requested="gpt-test",
        selected_provider="openai",
        selected_model="gpt-4o-mini",
        fallback_used=True,
        estimated_revenue_brl=3.0,
        estimated_cost_brl=1.0,
        estimated_margin_brl=2.0,
    )
    await process_pending_events(session)
    event = (await session.execute(select(CommercialRoutingEvent))).scalars().first()
    event.actual_revenue_brl = 3.0
    event.actual_cost_brl = 1.25
    event.actual_margin_brl = 1.75
    event.latency_ms = 120
    ingest = (await session.execute(select(CommercialRoutingEventIngest))).scalars().first()

    result = await aggregate_bucket(session, ingest.received_at)
    await session.commit()

    aggregate = (await session.execute(select(CommercialClusterAggregate))).scalars().first()
    assert result["aggregate_rows"] >= 1
    assert aggregate.requests_count == 1
    assert aggregate.fallback_count == 1


@pytest.mark.asyncio
async def test_cluster_overview_empty(session, monkeypatch):
    _enable_distributed(monkeypatch)
    overview = await get_cluster_overview(session, hours=24)
    assert overview["cluster_id"] == "cluster-test"
    assert overview["requests_count"] == 0
    assert overview["health"]["total_nodes"] == 0


@pytest.mark.asyncio
async def test_cluster_overview_populated(session, monkeypatch):
    _enable_distributed(monkeypatch)
    identity = resolve_node_identity()
    await write_heartbeat(session, identity)
    await commercial_analytics.record_routing_event(
        session,
        request_id="req-overview",
        correlation_id="corr-overview",
        model_requested="gpt-test",
        selected_provider="openai",
        selected_model="gpt-4o-mini",
        estimated_revenue_brl=4.0,
        estimated_cost_brl=1.5,
        estimated_margin_brl=2.5,
    )
    event = (await session.execute(select(CommercialRoutingEvent))).scalars().first()
    event.actual_revenue_brl = 4.0
    event.actual_cost_brl = 2.0
    event.actual_margin_brl = 2.0
    event.latency_ms = 150

    overview = await get_cluster_overview(session, hours=24)
    await session.commit()

    assert overview["requests_count"] >= 1
    assert overview["health"]["counts"]["healthy"] == 1
    assert overview["nodes"][0]["node_id"] == "node-test-1"


@pytest.mark.asyncio
async def test_cleanup_retention(session, monkeypatch):
    _enable_distributed(monkeypatch)
    old_time = utc_now() - timedelta(days=45)
    session.add(
        CommercialNodeHeartbeat(
            node_id="node-old",
            node_role="worker",
            hostname="old-host",
            started_at=old_time,
            last_seen_at=old_time,
            status="offline",
            metadata_json={},
        )
    )
    session.add(
        CommercialRoutingEventIngest(
            node_id="node-old",
            status="processed",
            dedupe_key="req:old",
            request_id="old",
            received_at=old_time,
            processed_at=old_time,
            payload_json={},
        )
    )
    session.add(
        CommercialClusterAggregate(
            bucket_start=old_time,
            bucket_minutes=5,
            node_id="node-old",
            requests_count=1,
            fallback_count=0,
            block_count=0,
            estimated_revenue_brl=1,
            estimated_cost_brl=1,
            actual_revenue_brl=1,
            actual_cost_brl=1,
            actual_margin_brl=0,
            avg_latency_ms=10,
            error_count=0,
        )
    )
    session.add(CommercialRoutingEvent(request_id="keep-main"))
    await session.flush()

    result = await cleanup_old_analytics(session)
    await session.commit()

    assert result["ingest_deleted"] == 1
    assert result["aggregate_deleted"] == 1
    assert result["heartbeat_deleted"] == 1
    assert (await session.execute(select(CommercialRoutingEvent).where(CommercialRoutingEvent.request_id == "keep-main"))).scalars().one()


@pytest.mark.asyncio
async def test_endpoints_require_admin_auth(admin_client, monkeypatch):
    _enable_distributed(monkeypatch)
    nodes = await admin_client.get("/admin/routing/distributed/nodes")
    overview = await admin_client.get("/admin/routing/distributed/cluster-overview")
    ingest = await admin_client.post("/admin/routing/distributed/ingest", json={"request_id": "req-auth"})

    assert nodes.status_code == 401
    assert overview.status_code == 401
    assert ingest.status_code == 401


@pytest.mark.asyncio
async def test_payload_sanitized(session, monkeypatch):
    _enable_distributed(monkeypatch)
    await ingest_routing_event(
        session,
        {
            "request_id": "req-redact",
            "prompt": "secret prompt",
            "authorization": "Bearer sk-secret-value",
            "notes": "token=abc123",
        },
        "node-a",
    )
    await session.commit()

    row = (await session.execute(select(CommercialRoutingEventIngest))).scalars().one()
    assert row.payload_json["prompt"] == "[REDACTED]"
    assert row.payload_json["authorization"] == "[REDACTED]"
    assert row.payload_json["notes"] == "[REDACTED]"


@pytest.mark.asyncio
async def test_best_effort_db_failure_does_not_raise(monkeypatch):
    _enable_distributed(monkeypatch)

    class BrokenSession:
        def add(self, *_args, **_kwargs):
            return None

        async def flush(self):
            raise RuntimeError("db token=secret failure")

    result = await commercial_analytics.record_routing_event(
        BrokenSession(),
        request_id="req-fail",
        selected_provider="openai",
    )
    assert result is None


@pytest.mark.asyncio
async def test_cluster_health_summary(session, monkeypatch):
    _enable_distributed(monkeypatch)
    await write_heartbeat(session, resolve_node_identity())
    summary = await summarize_cluster_health(session)
    assert summary["cluster_id"] == "cluster-test"
    assert summary["counts"]["healthy"] == 1
