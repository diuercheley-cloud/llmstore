# Owner: agent-platform
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.services.agents.analytics.analytics_aggregator import AnalyticsAggregator
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def mock_db():
    return MagicMock(spec=AsyncSession)

@pytest.mark.asyncio
async def test_analytics_aggregator_success(mock_db):
    aggregator = AnalyticsAggregator(mock_db)
    tenant_id = "tenant_123"
    
    # Mocking all queries
    with MagicMock() as mock_queries:
        mock_queries.get_run_success_rate = AsyncMock(return_value={"total": 100, "success_rate": 0.9, "distribution": {}})
        mock_queries.get_cost_and_tokens = AsyncMock(return_value={"total_cost_brl": 10.5, "total_tokens": 5000})
        mock_queries.get_tool_metrics = AsyncMock(return_value={"total_tool_calls": 50, "tool_failure_rate": 0.05})
        mock_queries.get_policy_denials = AsyncMock(return_value=5)
        mock_queries.get_eval_pass_rate = AsyncMock(return_value=0.85)
        
        aggregator.queries = mock_queries
        
        data = await aggregator.get_dashboard_data(tenant_id)
        
        assert data["run_metrics"]["total_runs"] == 100
        assert data["financial_metrics"]["total_cost_brl"] == 10.5
        assert data["operational_metrics"]["policy_denials_count"] == 5
        assert data["operational_metrics"]["eval_pass_rate"] == 0.85

@pytest.mark.asyncio
async def test_analytics_no_data(mock_db):
    aggregator = AnalyticsAggregator(mock_db)
    
    with MagicMock() as mock_queries:
        mock_queries.get_run_success_rate = AsyncMock(return_value={"total": 0, "success_rate": 0, "distribution": {}})
        # ... other mocks not needed as we stop if total_runs == 0 in API (or check here)
        
        aggregator.queries = mock_queries
        data = await aggregator.get_dashboard_data("tenant_empty")
        
        assert data["run_metrics"]["total_runs"] == 0
