import pytest
from unittest.mock import MagicMock
from app.domains.billing.contracts import BillingRepository, BillingPlanData
from app.domains.billing.repositories import SqlAlchemyBillingRepository

@pytest.mark.asyncio
async def test_billing_repository_contract():
    db = MagicMock()
    repo = SqlAlchemyBillingRepository(db)
    assert isinstance(repo, BillingRepository)

def test_billing_plan_data_schema():
    plan = BillingPlanData(
        code="test",
        name="Test Plan",
        rate_limit_per_minute=10,
        daily_token_quota=100,
        weekly_token_quota=500,
        monthly_token_quota=2000,
        max_output_tokens=50,
        allow_streaming=True
    )
    assert plan.code == "test"
    assert plan.max_context_tokens == 4096 # default
    assert plan.rag_enabled is False # default
