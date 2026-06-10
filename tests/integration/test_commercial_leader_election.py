from __future__ import annotations

from datetime import timedelta

import httpx
import pytest
from app.api.commercial_ha_admin import router as commercial_ha_admin_router
from app.core.config import get_settings
from app.core.time import utc_now
from app.models.commercial.commercial_leader_lease import CommercialLeaderLease
from app.models.commercial.commercial_node_heartbeat import CommercialNodeHeartbeat
from app.services.routing.commercial_cluster_aggregates import (
    cleanup_old_analytics,
    rebuild_aggregates,
)
from app.services.routing.commercial_leader_election import (
    force_expire_stale_leases,
    get_current_leader,
    is_current_leader,
    renew_leader_lease,
    try_acquire_leader,
    validate_fencing_token,
)
from fastapi import FastAPI
from sqlalchemy import select


def _enable_ha(monkeypatch: pytest.MonkeyPatch, *, node_id: str = "node-a") -> None:
    monkeypatch.setenv("COMMERCIAL_LEADER_ELECTION_ENABLED", "true")
    monkeypatch.setenv("COMMERCIAL_LEADER_FENCING_ENABLED", "true")
    monkeypatch.setenv("COMMERCIAL_LEASE_DURATION_SECONDS", "60")
    monkeypatch.setenv("COMMERCIAL_LEASE_HEARTBEAT_SECONDS", "15")
    monkeypatch.setenv("COMMERCIAL_LEASE_RENEW_BEFORE_SECONDS", "20")
    monkeypatch.setenv("COMMERCIAL_LEASE_MAX_CLOCK_SKEW_SECONDS", "0")
    monkeypatch.setenv("COMMERCIAL_DISTRIBUTED_ANALYTICS_ENABLED", "true")
    monkeypatch.setenv("COMMERCIAL_ANALYTICS_RETENTION_DAYS", "30")
    monkeypatch.setenv("NODE_ID", node_id)
    monkeypatch.setenv("NODE_ROLE", "scheduler")
    monkeypatch.setenv("CLUSTER_ID", "cluster-ha-test")
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_acquire_leader(session, monkeypatch):
    _enable_ha(monkeypatch)
    result = await try_acquire_leader(
        session,
        cluster_id="cluster-ha-test",
        leader_role="aggregator",
        node_id="node-a",
        metadata_json={"safe": True},
    )
    await session.commit()

    assert result["acquired"] is True
    assert result["lease"]["node_id"] == "node-a"
    assert result["lease"]["lease_token"] == 1


@pytest.mark.asyncio
async def test_second_node_rejected(session, monkeypatch):
    _enable_ha(monkeypatch)
    first = await try_acquire_leader(session, cluster_id="cluster-ha-test", leader_role="aggregator", node_id="node-a")
    second = await try_acquire_leader(session, cluster_id="cluster-ha-test", leader_role="aggregator", node_id="node-b")
    await session.commit()

    assert first["acquired"] is True
    assert second["acquired"] is False
    assert second["reason"] == "leader_exists"


@pytest.mark.asyncio
async def test_lease_renew(session, monkeypatch):
    _enable_ha(monkeypatch)
    lease = await try_acquire_leader(session, cluster_id="cluster-ha-test", leader_role="reporter", node_id="node-a")
    first_expiry = lease["lease"]["lease_expires_at"]
    renewed = await renew_leader_lease(
        session,
        cluster_id="cluster-ha-test",
        leader_role="reporter",
        node_id="node-a",
        lease_token=lease["lease"]["lease_token"],
    )
    await session.commit()

    assert renewed["renewed"] is True
    assert renewed["lease"]["lease_expires_at"] >= first_expiry


@pytest.mark.asyncio
async def test_lease_expire(session, monkeypatch):
    _enable_ha(monkeypatch)
    lease = await try_acquire_leader(session, cluster_id="cluster-ha-test", leader_role="reporter", node_id="node-a")
    row = (await session.execute(select(CommercialLeaderLease))).scalars().one()
    row.lease_expires_at = utc_now() - timedelta(seconds=1)
    expired = await force_expire_stale_leases(session, cluster_id="cluster-ha-test", leader_role="reporter")
    current = await get_current_leader(session, cluster_id="cluster-ha-test", leader_role="reporter")
    await session.commit()

    assert lease["acquired"] is True
    assert expired["expired_count"] == 1
    assert current is None


@pytest.mark.asyncio
async def test_failover(session, monkeypatch):
    _enable_ha(monkeypatch)
    first = await try_acquire_leader(session, cluster_id="cluster-ha-test", leader_role="aggregator", node_id="node-a")
    row = (await session.execute(select(CommercialLeaderLease))).scalars().one()
    row.lease_expires_at = utc_now() - timedelta(seconds=1)
    await force_expire_stale_leases(session, cluster_id="cluster-ha-test", leader_role="aggregator")
    second = await try_acquire_leader(session, cluster_id="cluster-ha-test", leader_role="aggregator", node_id="node-b")
    await session.commit()

    assert second["acquired"] is True
    assert second["lease"]["node_id"] == "node-b"
    assert second["lease"]["lease_token"] > first["lease"]["lease_token"]


@pytest.mark.asyncio
async def test_fencing_token_grows(session, monkeypatch):
    _enable_ha(monkeypatch)
    first = await try_acquire_leader(session, cluster_id="cluster-ha-test", leader_role="canary", node_id="node-a")
    row = (await session.execute(select(CommercialLeaderLease))).scalars().one()
    row.lease_expires_at = utc_now() - timedelta(seconds=1)
    await force_expire_stale_leases(session, cluster_id="cluster-ha-test", leader_role="canary")
    second = await try_acquire_leader(session, cluster_id="cluster-ha-test", leader_role="canary", node_id="node-b")
    await session.commit()

    assert second["lease"]["lease_token"] == first["lease"]["lease_token"] + 1


@pytest.mark.asyncio
async def test_stale_lease_expires_when_node_offline(session, monkeypatch):
    _enable_ha(monkeypatch)
    session.add(
        CommercialNodeHeartbeat(
            node_id="node-a",
            node_role="scheduler",
            hostname="host-a",
            started_at=utc_now() - timedelta(minutes=10),
            last_seen_at=utc_now() - timedelta(minutes=10),
            status="healthy",
            metadata_json={},
        )
    )
    await try_acquire_leader(session, cluster_id="cluster-ha-test", leader_role="global", node_id="node-a")
    expired = await force_expire_stale_leases(session, cluster_id="cluster-ha-test", leader_role="global")
    await session.commit()

    assert expired["expired_count"] == 1


@pytest.mark.asyncio
async def test_scheduler_singleton(session, monkeypatch):
    _enable_ha(monkeypatch)
    leader = await try_acquire_leader(session, cluster_id="cluster-ha-test", leader_role="reporter", node_id="node-a")
    follower = await try_acquire_leader(session, cluster_id="cluster-ha-test", leader_role="reporter", node_id="node-b")
    await session.commit()

    assert leader["acquired"] is True
    assert follower["acquired"] is False
    assert await is_current_leader(
        session,
        cluster_id="cluster-ha-test",
        leader_role="reporter",
        node_id="node-a",
        lease_token=leader["lease"]["lease_token"],
    )


@pytest.mark.asyncio
async def test_cleanup_not_execute_on_follower(session, monkeypatch):
    _enable_ha(monkeypatch)
    leader = await try_acquire_leader(session, cluster_id="cluster-ha-test", leader_role="aggregator", node_id="node-a")
    rejected = await cleanup_old_analytics(
        session,
        cluster_id="cluster-ha-test",
        node_id="node-b",
        lease_token=leader["lease"]["lease_token"],
    )
    await session.commit()

    assert rejected["executed"] is False
    assert rejected["reason"] == "fencing_rejected"


@pytest.mark.asyncio
async def test_rebuild_not_execute_on_follower(session, monkeypatch):
    _enable_ha(monkeypatch)
    leader = await try_acquire_leader(session, cluster_id="cluster-ha-test", leader_role="aggregator", node_id="node-a")
    rejected = await rebuild_aggregates(
        session,
        cluster_id="cluster-ha-test",
        node_id="node-b",
        lease_token=leader["lease"]["lease_token"],
    )
    await session.commit()

    assert rejected["executed"] is False
    assert rejected["reason"] == "fencing_rejected"


@pytest.mark.asyncio
async def test_split_brain_avoided(session, monkeypatch):
    _enable_ha(monkeypatch)
    first = await try_acquire_leader(session, cluster_id="cluster-ha-test", leader_role="aggregator", node_id="node-a")
    second = await try_acquire_leader(session, cluster_id="cluster-ha-test", leader_role="aggregator", node_id="node-b")
    valid_old = await validate_fencing_token(
        session,
        cluster_id="cluster-ha-test",
        leader_role="aggregator",
        lease_token=first["lease"]["lease_token"],
        node_id="node-a",
    )
    await session.commit()

    assert first["acquired"] is True
    assert second["acquired"] is False
    assert valid_old is True


@pytest.mark.asyncio
async def test_endpoints_require_admin_auth():
    app = FastAPI()
    app.include_router(commercial_ha_admin_router)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        for path in [
            "/admin/routing/ha/leaders",
            "/admin/routing/ha/cluster-state",
            "/admin/routing/ha/force-expire",
            "/admin/routing/ha/release",
            "/admin/routing/ha/acquire",
        ]:
            if path.endswith(("force-expire", "release", "acquire")):
                response = await client.post(path, json={})
            else:
                response = await client.get(path)
            assert response.status_code == 401


@pytest.mark.asyncio
async def test_payload_sanitized(session, monkeypatch):
    _enable_ha(monkeypatch)
    acquired = await try_acquire_leader(
        session,
        cluster_id="cluster-ha-test",
        leader_role="global",
        node_id="node-a",
        metadata_json={"api_key": "sk-secret-value", "prompt": "secret prompt", "safe": "ok"},
    )
    row = (await session.execute(select(CommercialLeaderLease))).scalars().one()
    await session.commit()

    assert acquired["lease"]["metadata_json"]["api_key"] == "[REDACTED]"
    assert row.metadata_json["prompt"] == "[REDACTED]"
    assert row.metadata_json["safe"] == "ok"
