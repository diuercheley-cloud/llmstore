from __future__ import annotations

import pytest
from app.models.commercial.global_routing_policy import GlobalRoutingPolicyVersion
from sqlalchemy import select


@pytest.mark.asyncio
async def test_commercial_global_routing_governance(admin_client, admin_token_headers, session):
    # 1. Simulate policy (should not alter active policy)
    policy_json = {
        "commercial_global_routing_enabled": True,
        "commercial_global_routing_mode": "recommend_only",
        "commercial_global_routing_margin_weight": 0.50,
        "commercial_global_routing_latency_weight": 0.20,
        "commercial_global_routing_health_weight": 0.10,
        "commercial_global_routing_region_weight": 0.10,
        "commercial_global_routing_priority_weight": 0.10,
        "commercial_global_routing_require_healthy_cluster": True,
        "commercial_global_routing_allow_cross_region": False,
        "commercial_global_routing_max_latency_ms": 4000,
    }

    sim_resp = await admin_client.post(
        "/admin/routing/global-router/policies/simulate",
        headers=admin_token_headers,
        json={"policy_json": policy_json, "tenant_id": "tenant-test", "estimated_tokens": 100},
    )
    assert sim_resp.status_code == 200
    # Verify no active policy exists in the DB yet
    db_res = await session.execute(
        select(GlobalRoutingPolicyVersion)
        .where(GlobalRoutingPolicyVersion.status == "active")
        .execution_options(populate_existing=True)
    )
    assert db_res.scalars().first() is None

    # 2. Create draft
    draft_resp = await admin_client.post(
        "/admin/routing/global-router/policies/draft",
        headers=admin_token_headers,
        json={"policy_json": policy_json, "created_by": "test-user"},
    )
    assert draft_resp.status_code == 200
    draft_data = draft_resp.json()
    assert draft_data["status"] == "draft"
    assert draft_data["version"] == 1
    policy_id_1 = draft_data["id"]

    # 3. Invalid policy validation
    invalid_policy_json = policy_json.copy()
    invalid_policy_json["commercial_global_routing_margin_weight"] = (
        0.10  # sum of weights is now 0.60
    )

    invalid_draft_resp = await admin_client.post(
        "/admin/routing/global-router/policies/draft",
        headers=admin_token_headers,
        json={"policy_json": invalid_policy_json, "created_by": "test-user"},
    )
    assert invalid_draft_resp.status_code == 200
    invalid_policy_id = invalid_draft_resp.json()["id"]

    # Attempt to activate invalid policy
    activate_invalid_resp = await admin_client.post(
        f"/admin/routing/global-router/policies/{invalid_policy_id}/activate",
        headers=admin_token_headers,
    )
    assert activate_invalid_resp.status_code == 400

    # 4. Activate draft 1
    activate_resp = await admin_client.post(
        f"/admin/routing/global-router/policies/{policy_id_1}/activate", headers=admin_token_headers
    )
    assert activate_resp.status_code == 200
    activated_data = activate_resp.json()
    assert activated_data["status"] == "active"
    assert activated_data["previous_version_id"] is None

    # Verify it is active in the database
    db_res = await session.execute(
        select(GlobalRoutingPolicyVersion)
        .where(GlobalRoutingPolicyVersion.status == "active")
        .execution_options(populate_existing=True)
    )
    db_active = db_res.scalars().first()
    assert db_active is not None
    assert str(db_active.id) == policy_id_1

    # Check overview endpoint returns activated configuration values (runtime integration validation)
    overview_resp = await admin_client.get(
        "/admin/routing/global-router/overview", headers=admin_token_headers
    )
    assert overview_resp.status_code == 200
    overview_data = overview_resp.json()
    assert overview_data["config"]["margin_weight"] == 0.50
    assert overview_data["config"]["max_latency_ms"] == 4000

    # 5. Create and activate draft 2
    policy_json_2 = policy_json.copy()
    policy_json_2["commercial_global_routing_margin_weight"] = 0.60
    policy_json_2["commercial_global_routing_latency_weight"] = 0.10

    draft_resp_2 = await admin_client.post(
        "/admin/routing/global-router/policies/draft",
        headers=admin_token_headers,
        json={"policy_json": policy_json_2, "created_by": "test-user"},
    )
    assert draft_resp_2.status_code == 200
    policy_id_2 = draft_resp_2.json()["id"]

    activate_resp_2 = await admin_client.post(
        f"/admin/routing/global-router/policies/{policy_id_2}/activate", headers=admin_token_headers
    )
    assert activate_resp_2.status_code == 200
    activated_data_2 = activate_resp_2.json()
    assert activated_data_2["status"] == "active"
    assert activated_data_2["previous_version_id"] == policy_id_1

    # Verify version 1 is now "rolled_back" and version 2 is active
    db_res_1 = await session.execute(
        select(GlobalRoutingPolicyVersion)
        .where(GlobalRoutingPolicyVersion.id == db_active.id)
        .execution_options(populate_existing=True)
    )
    db_active_updated = db_res_1.scalars().first()
    assert db_active_updated.status == "rolled_back"

    # Check overview returns updated version 2 settings
    overview_resp_2 = await admin_client.get(
        "/admin/routing/global-router/overview", headers=admin_token_headers
    )
    overview_data_2 = overview_resp_2.json()
    assert overview_data_2["config"]["margin_weight"] == 0.60

    # 6. Rollback to version 1
    rollback_resp = await admin_client.post(
        "/admin/routing/global-router/policies/rollback", headers=admin_token_headers
    )
    assert rollback_resp.status_code == 200
    rollback_data = rollback_resp.json()
    assert rollback_data["status"] == "active"
    assert rollback_data["id"] == policy_id_1

    # Check version 2 is now "rolled_back"
    db_res_2 = await session.execute(
        select(GlobalRoutingPolicyVersion)
        .where(GlobalRoutingPolicyVersion.id == db_active_updated.id)
        .execution_options(populate_existing=True)
    )
    db_version_1 = db_res_2.scalars().first()
    assert db_version_1.status == "active"

    # Verify overview returns version 1 settings again
    overview_resp_3 = await admin_client.get(
        "/admin/routing/global-router/overview", headers=admin_token_headers
    )
    overview_data_3 = overview_resp_3.json()
    assert overview_data_3["config"]["margin_weight"] == 0.50
