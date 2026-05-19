import pytest
from app.services.enterprise_onboarding import EnterpriseOnboardingService

@pytest.mark.asyncio
async def test_enterprise_project_creation(db_session):
    service = EnterpriseOnboardingService(db_session)
    customer = await service.create_customer("Enterprise Corp", "admin@enterprise.com")
    project = await service.create_project(customer.id, "Pilot Q3 2026")
    
    assert project.name == "Pilot Q3 2026"
    assert project.status == "discovery"
    assert len(project.tasks) == 10 # Default tasks

@pytest.mark.asyncio
async def test_task_completion_lifecycle(db_session):
    service = EnterpriseOnboardingService(db_session)
    customer = await service.create_customer("Test Client", "test@client.com")
    project = await service.create_project(customer.id, "Test Project")
    
    task = project.tasks[0]
    updated_task = await service.update_task_status(task.id, "completed", notes="Workshop done")
    
    assert updated_task.status == "completed"
    assert updated_task.notes == "Workshop done"
    assert updated_task.completed_at is not None
