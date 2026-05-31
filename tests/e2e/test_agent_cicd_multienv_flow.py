import uuid

import pytest


@pytest.mark.asyncio
async def test_agent_cicd_multienvironment_rollout_and_rollback(e2e_client, admin_headers):
    from app.db.session import SessionLocal
    from app.models.agents import AgentDefinition

    tenant_id = str(uuid.uuid4())
    agent_id = uuid.uuid4()

    async with SessionLocal() as session:
        session.add(
            AgentDefinition(
                id=agent_id,
                tenant_id=tenant_id,
                name="CI/CD E2E Agent",
                version="1.0.0",
                instructions="Execute staged and production rollout.",
                model_id="mock-model",
                owner="e2e-cicd",
                status="active",
                allowed_tools=[],
                max_steps=4,
                max_runtime_seconds=120,
            )
        )
        await session.commit()

    first_pipeline_resp = await e2e_client.post(
        "/admin/agents/cicd/pipelines",
        json={
            "agent_id": str(agent_id),
            "tenant_id": tenant_id,
            "config": {
                "promotion_environments": ["staging", "production"],
                "production_approved": True,
                "version_tag": "v1",
                "rollout_weights": [0.25, 1.0],
            },
        },
        headers=admin_headers,
    )
    assert first_pipeline_resp.status_code == 200
    first_pipeline_id = first_pipeline_resp.json()["id"]

    first_run_resp = await e2e_client.post(
        f"/admin/agents/cicd/pipelines/{first_pipeline_id}/run",
        headers=admin_headers,
    )
    assert first_run_resp.status_code == 200
    assert first_run_resp.json()["status"] == "completed"

    first_details_resp = await e2e_client.get(
        f"/admin/agents/cicd/pipelines/{first_pipeline_id}",
        headers=admin_headers,
    )
    assert first_details_resp.status_code == 200
    first_payload = first_details_resp.json()
    first_deployments = first_payload["deployments"]
    assert {item["environment"] for item in first_deployments} == {"staging", "production"}
    assert all(item["status"] == "completed" for item in first_deployments)

    second_pipeline_resp = await e2e_client.post(
        "/admin/agents/cicd/pipelines",
        json={
            "agent_id": str(agent_id),
            "tenant_id": tenant_id,
            "config": {
                "promotion_environments": ["staging", "production"],
                "production_approved": True,
                "version_tag": "v2",
                "rollout_weights": [0.1, 0.5, 1.0],
            },
        },
        headers=admin_headers,
    )
    assert second_pipeline_resp.status_code == 200
    second_pipeline_id = second_pipeline_resp.json()["id"]

    second_run_resp = await e2e_client.post(
        f"/admin/agents/cicd/pipelines/{second_pipeline_id}/run",
        headers=admin_headers,
    )
    assert second_run_resp.status_code == 200
    assert second_run_resp.json()["status"] == "completed"

    second_details_resp = await e2e_client.get(
        f"/admin/agents/cicd/pipelines/{second_pipeline_id}",
        headers=admin_headers,
    )
    assert second_details_resp.status_code == 200
    second_payload = second_details_resp.json()
    production_deployment = next(
        item for item in second_payload["deployments"] if item["environment"] == "production"
    )
    assert production_deployment["version_tag"] == "v2"
    assert production_deployment["traffic_weight"] == 1.0

    rollback_resp = await e2e_client.post(
        f"/admin/agents/cicd/deployments/{production_deployment['id']}/rollback",
        json={"reason": "Regression detected in production canary"},
        headers=admin_headers,
    )
    assert rollback_resp.status_code == 200
    rollback_payload = rollback_resp.json()
    assert rollback_payload["status"] == "completed"
    assert rollback_payload["from_version"] == "v2"
    assert rollback_payload["to_version"] == "v1"
