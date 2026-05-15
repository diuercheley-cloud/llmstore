from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.commercial_cluster_aggregate import CommercialClusterAggregate
from app.models.commercial_cluster_registry import CommercialClusterRegistry
from app.models.commercial_federated_aggregate import CommercialFederatedAggregate
from app.services.routing.commercial_cluster_registry import list_clusters, register_cluster, update_cluster_status


def _enable_federation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMMERCIAL_FEDERATION_ENABLED", "true")
    monkeypatch.setenv("COMMERCIAL_CLUSTER_ID", "local-main")
    monkeypatch.setenv("COMMERCIAL_CLUSTER_REGION", "local")
    monkeypatch.setenv("COMMERCIAL_CLUSTER_ENVIRONMENT", "local")
    monkeypatch.setenv("COMMERCIAL_FEDERATION_MODE", "local_only")
    monkeypatch.setenv("COMMERCIAL_FEDERATION_SYNC_INTERVAL_SECONDS", "300")
    monkeypatch.setenv("COMMERCIAL_FEDERATION_RETENTION_DAYS", "180")
    monkeypatch.setenv("COMMERCIAL_FEDERATION_ALLOW_PUSH", "false")
    monkeypatch.setenv("COMMERCIAL_FEDERATION_REQUIRE_TOKEN", "true")
    monkeypatch.setenv("COMMERCIAL_FEDERATION_SHARED_TOKEN", "shared-fed-token")
    get_settings.cache_clear()


async def _seed_local_aggregate(session, *, provider: str = "openai", model: str = "gpt-4o-mini", margin: float = 2.5):
    session.add(
        CommercialClusterAggregate(
            bucket_start=utc_now() - timedelta(minutes=5),
            bucket_minutes=5,
            node_id="node-local",
            provider=provider,
            model=model,
            client_id="client-local",
            requests_count=10,
            fallback_count=1,
            block_count=0,
            estimated_revenue_brl=8.0,
            estimated_cost_brl=4.0,
            actual_revenue_brl=8.0,
            actual_cost_brl=5.5,
            actual_margin_brl=margin,
            avg_latency_ms=120,
            error_count=0,
        )
    )
    await session.flush()


@pytest.mark.asyncio
async def test_register_cluster(session, monkeypatch):
    _enable_federation(monkeypatch)
    row = await register_cluster(
        session,
        cluster_id="remote-a",
        name="Remote A",
        region="us-east-1",
        environment="production",
        tenant_scope_json={"tenants": ["tenant-a"], "allow_untagged": False},
        metadata_json={"api_key": "secret-value", "note": "safe"},
    )
    await session.commit()

    assert row.cluster_id == "remote-a"
    assert row.metadata_json["api_key"] == "[REDACTED]"


@pytest.mark.asyncio
async def test_list_clusters(session, monkeypatch):
    _enable_federation(monkeypatch)
    await register_cluster(session, cluster_id="remote-b", name="Remote B", region="eu-west-1", environment="staging")
    rows = await list_clusters(session)
    await session.commit()

    cluster_ids = {row["cluster_id"] for row in rows}
    assert "local-main" in cluster_ids
    assert "remote-b" in cluster_ids


@pytest.mark.asyncio
async def test_update_status(session, monkeypatch):
    _enable_federation(monkeypatch)
    await register_cluster(session, cluster_id="remote-c", name="Remote C")
    updated = await update_cluster_status(session, cluster_id="remote-c", status="degraded")
    await session.commit()

    assert updated is not None
    assert updated.status == "degraded"


@pytest.mark.asyncio
async def test_ingest_aggregate_valido(admin_client, admin_token_headers, session, monkeypatch):
    _enable_federation(monkeypatch)
    await register_cluster(
        session,
        cluster_id="remote-prod",
        name="Remote Prod",
        environment="production",
        tenant_scope_json={"tenants": ["tenant-1"], "allow_untagged": False},
    )
    await session.commit()
    payload = {
        "source_cluster_id": "remote-prod",
        "aggregates": [
            {
                "bucket_start": utc_now().isoformat(),
                "bucket_minutes": 5,
                "provider": "openai",
                "model": "gpt-4o-mini",
                "client_id": "client-1",
                "tenant_id": "tenant-1",
                "requests_count": 5,
                "actual_cost_brl": 2.0,
                "actual_margin_brl": 1.5,
                "avg_latency_ms": 110,
                "received_at": utc_now().isoformat(),
            }
        ],
    }
    response = await admin_client.post(
        "/admin/routing/federation/ingest",
        headers={"X-Federation-Token": "shared-fed-token"},
        json=payload,
    )

    assert response.status_code == 200
    assert response.json()["records_processed"] == 1


@pytest.mark.asyncio
async def test_ingest_duplicado(admin_client, session, monkeypatch):
    _enable_federation(monkeypatch)
    await register_cluster(session, cluster_id="remote-dup", name="Remote Dup", tenant_scope_json={"tenants": ["tenant-1"]})
    await session.commit()
    payload = {
        "source_cluster_id": "remote-dup",
        "aggregates": [
            {
                "bucket_start": utc_now().isoformat(),
                "bucket_minutes": 5,
                "provider": "openai",
                "model": "gpt-4o-mini",
                "client_id": "client-dup",
                "tenant_id": "tenant-1",
                "requests_count": 2,
            }
        ],
    }
    first = await admin_client.post("/admin/routing/federation/ingest", headers={"X-Federation-Token": "shared-fed-token"}, json=payload)
    second = await admin_client.post("/admin/routing/federation/ingest", headers={"X-Federation-Token": "shared-fed-token"}, json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["records_duplicate"] == 1


@pytest.mark.asyncio
async def test_ingest_sem_token_rejeitado(admin_client, monkeypatch):
    _enable_federation(monkeypatch)
    response = await admin_client.post("/admin/routing/federation/ingest", json={"source_cluster_id": "remote-x", "aggregates": []})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_ingest_token_invalido_rejeitado(admin_client, monkeypatch):
    _enable_federation(monkeypatch)
    response = await admin_client.post(
        "/admin/routing/federation/ingest",
        headers={"X-Federation-Token": "wrong-token"},
        json={"source_cluster_id": "remote-x", "aggregates": []},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_tenant_fora_do_escopo_rejeitado(admin_client, session, monkeypatch):
    _enable_federation(monkeypatch)
    await register_cluster(
        session,
        cluster_id="remote-scope",
        name="Remote Scope",
        tenant_scope_json={"tenants": ["tenant-allow"], "allow_untagged": False},
    )
    await session.commit()
    response = await admin_client.post(
        "/admin/routing/federation/ingest",
        headers={"X-Federation-Token": "shared-fed-token"},
        json={
            "source_cluster_id": "remote-scope",
            "aggregates": [
                {
                    "bucket_start": utc_now().isoformat(),
                    "bucket_minutes": 5,
                    "provider": "openai",
                    "tenant_id": "tenant-blocked",
                    "requests_count": 1,
                }
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["records_processed"] == 0
    assert response.json()["records_rejected"] == 1


@pytest.mark.asyncio
async def test_overview_federado_vazio(admin_client, admin_token_headers, monkeypatch):
    _enable_federation(monkeypatch)
    response = await admin_client.get("/admin/routing/federation/overview", headers=admin_token_headers)
    payload = response.json()

    assert response.status_code == 200
    assert payload["requests_count"] == 0
    assert payload["clusters_registered"] >= 1


@pytest.mark.asyncio
async def test_overview_federado_populado(admin_client, admin_token_headers, session, monkeypatch):
    _enable_federation(monkeypatch)
    await _seed_local_aggregate(session)
    await register_cluster(session, cluster_id="remote-overview", name="Remote Overview", tenant_scope_json={"tenants": ["tenant-1"]})
    session.add(
        CommercialFederatedAggregate(
            source_cluster_id="remote-overview",
            bucket_start=utc_now() - timedelta(minutes=5),
            bucket_minutes=5,
            provider="deepseek",
            model="deepseek-chat",
            client_id="client-remote",
            tenant_id="tenant-1",
            requests_count=4,
            actual_cost_brl=1.0,
            actual_margin_brl=1.2,
            avg_latency_ms=90,
            dedupe_key="remote-overview|x|deepseek|deepseek-chat|client-remote|tenant-1",
            received_at=utc_now(),
        )
    )
    await session.commit()

    response = await admin_client.get("/admin/routing/federation/overview", headers=admin_token_headers)
    payload = response.json()

    assert response.status_code == 200
    assert payload["requests_count"] == 14
    assert len(payload["clusters"]) >= 2


@pytest.mark.asyncio
async def test_compare_clusters(admin_client, admin_token_headers, session, monkeypatch):
    _enable_federation(monkeypatch)
    await _seed_local_aggregate(session, margin=3.0)
    await register_cluster(session, cluster_id="remote-compare", name="Remote Compare", tenant_scope_json={"tenants": ["tenant-1"]})
    session.add(
        CommercialFederatedAggregate(
            source_cluster_id="remote-compare",
            bucket_start=utc_now() - timedelta(minutes=5),
            bucket_minutes=5,
            provider="openai",
            model="gpt-4o-mini",
            client_id="client-remote",
            tenant_id="tenant-1",
            requests_count=3,
            actual_cost_brl=1.5,
            actual_margin_brl=-0.2,
            avg_latency_ms=260,
            dedupe_key="remote-compare|x|openai|gpt-4o-mini|client-remote|tenant-1",
            received_at=utc_now(),
        )
    )
    await session.commit()

    response = await admin_client.get("/admin/routing/federation/compare", headers=admin_token_headers)
    payload = response.json()

    assert response.status_code == 200
    assert len(payload["comparisons"]) >= 2
    assert any(item["type"] in {"negative_margin", "latency_regression"} for item in payload["anomalies"])


@pytest.mark.asyncio
async def test_export_json_csv_html(admin_client, admin_token_headers, session, monkeypatch):
    _enable_federation(monkeypatch)
    await _seed_local_aggregate(session)
    await session.commit()

    json_resp = await admin_client.get("/admin/routing/federation/export?format=json", headers=admin_token_headers)
    csv_resp = await admin_client.get("/admin/routing/federation/export?format=csv", headers=admin_token_headers)
    html_resp = await admin_client.get("/admin/routing/federation/export?format=html", headers=admin_token_headers)

    assert json_resp.status_code == 200
    assert "overview" in json_resp.json()
    assert "source_cluster_id" in csv_resp.text
    assert "Commercial Federation" in html_resp.text


@pytest.mark.asyncio
async def test_cleanup_retention(admin_client, admin_token_headers, session, monkeypatch):
    _enable_federation(monkeypatch)
    session.add(
        CommercialFederatedAggregate(
            source_cluster_id="remote-clean",
            bucket_start=utc_now() - timedelta(days=181),
            bucket_minutes=5,
            provider="openai",
            model="gpt-4o-mini",
            client_id="client-clean",
            tenant_id="tenant-clean",
            requests_count=1,
            actual_cost_brl=1.0,
            actual_margin_brl=0.5,
            avg_latency_ms=10,
            dedupe_key="remote-clean|old|openai|gpt-4o-mini|client-clean|tenant-clean",
            received_at=utc_now() - timedelta(days=181),
        )
    )
    await session.commit()

    response = await admin_client.post("/admin/routing/federation/cleanup", headers=admin_token_headers)
    remaining = (await session.execute(select(CommercialFederatedAggregate))).scalars().all()

    assert response.status_code == 200
    assert response.json()["aggregate_deleted"] >= 1
    assert remaining == []


@pytest.mark.asyncio
async def test_payload_sanitizado(admin_client, admin_token_headers, session, monkeypatch):
    _enable_federation(monkeypatch)
    response = await admin_client.post(
        "/admin/routing/federation/clusters",
        headers=admin_token_headers,
        json={
            "cluster_id": "remote-safe",
            "name": "Remote Safe",
            "metadata_json": {"token": "secret-token", "nested": {"password": "x", "note": "ok"}},
        },
    )
    listing = await admin_client.get("/admin/routing/federation/clusters", headers=admin_token_headers)

    assert response.status_code == 200
    cluster = next(item for item in listing.json()["clusters"] if item["cluster_id"] == "remote-safe")
    assert cluster["metadata_json"]["token"] == "[REDACTED]"
    assert cluster["metadata_json"]["nested"]["password"] == "[REDACTED]"


@pytest.mark.asyncio
async def test_single_cluster_continua_funcionando(admin_client, admin_token_headers, session, monkeypatch):
    _enable_federation(monkeypatch)
    await _seed_local_aggregate(session, provider="lmstudio", model="local-model", margin=4.0)
    await session.commit()

    response = await admin_client.get("/admin/routing/federation/overview", headers=admin_token_headers)
    payload = response.json()

    assert response.status_code == 200
    assert payload["requests_count"] == 10
    assert any(item["cluster_id"] == "local-main" for item in payload["clusters"])
