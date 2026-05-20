import pytest
from app.services.chaos_engineering import ChaosEngineeringService
import os

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
