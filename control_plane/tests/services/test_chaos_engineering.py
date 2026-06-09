import os

import pytest
from app.services.chaos_engineering import ChaosEngineeringService


@pytest.mark.asyncio
async def test_chaos_disabled_by_default(db_session):
    service = ChaosEngineeringService(db_session)
    # Ensure env is set to false for test
    os.environ["CHAOS_ENABLED"] = "false"
    
    # Create experiment first
    await service.seed_default_experiments()
    experiments = await service.list_experiments()
    
    with pytest.raises(ValueError, match="Chaos Engineering is disabled"):
        await service.create_run(experiments[0].id)

@pytest.mark.asyncio
async def test_chaos_lifecycle_simulation(db_session):
    service = ChaosEngineeringService(db_session)
    os.environ["CHAOS_ENABLED"] = "true"
    os.environ["CHAOS_ENVIRONMENT"] = "test"
    
    await service.seed_default_experiments()
    experiments = await service.list_experiments()
    
    run = await service.create_run(experiments[0].id, operator_id="admin")
    assert run.status == "pending"
    
    await service.start_run(run.id)
    
    # Reload run
    await db_session.refresh(run)
    assert run.status == "completed"
    
    report = await service.get_report(run.id)
    assert report is not None
    assert report.resilience_score > 0

@pytest.mark.asyncio
async def test_chaos_status_reflects_environment(db_session, monkeypatch):
    service = ChaosEngineeringService(db_session)
    monkeypatch.setenv("CHAOS_ENABLED", "true")
    monkeypatch.setenv("CHAOS_ENVIRONMENT", "production")
    monkeypatch.setenv("CHAOS_ALLOW_PRODUCTION", "false")

    status = await service.get_status()

    assert status["enabled"] is True
    assert status["environment"] == "production"
    assert status["blocked_in_production"] is True
    assert status["state"] == "blocked"

@pytest.mark.asyncio
async def test_chaos_run_listing_includes_experiment_metadata(db_session, monkeypatch):
    service = ChaosEngineeringService(db_session)
    monkeypatch.setenv("CHAOS_ENABLED", "true")
    monkeypatch.setenv("CHAOS_ENVIRONMENT", "test")

    await service.seed_default_experiments()
    experiments = await service.list_experiments()

    run = await service.create_run(experiments[0].id, operator_id="admin")
    runs = await service.list_runs()

    assert len(runs) == 1
    assert runs[0]["id"] == run.id
    assert runs[0]["experiment_name"] == experiments[0].name
    assert runs[0]["experiment_type"] == experiments[0].experiment_type
    assert runs[0]["status"] == "pending"
