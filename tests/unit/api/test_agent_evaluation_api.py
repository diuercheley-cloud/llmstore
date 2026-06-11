import uuid

import pytest
from app.services.agents.agent_evaluation_framework import AgentEvaluationService


@pytest.mark.asyncio
async def test_agent_evaluation_export_endpoint(async_client, session, tmp_path, monkeypatch):
    service = AgentEvaluationService(session, artifacts_dir=tmp_path)
    report = await service.run_benchmark(uuid.uuid4(), 'demo-model', 'GAIA')

    from app.api import admin_evaluation
    monkeypatch.setattr(admin_evaluation, 'AgentEvaluationService', lambda db: AgentEvaluationService(db, artifacts_dir=tmp_path))

    resp = await async_client.get(f'/admin/evaluation/agent-evaluation/runs/{report.run_id}/export?benchmark=GAIA&format=json')
    assert resp.status_code == 200
    assert resp.json()['benchmark'] == 'GAIA'

