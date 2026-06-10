from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from app.services.billing.guardrails import (
    get_client_provider_cost_today,
    get_global_provider_cost_today,
    is_cloud_blocked_by_guardrails,
)


@pytest.mark.asyncio
async def test_get_global_provider_cost_today():
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar.return_value = 125.50
    session.execute.return_value = mock_result
    
    cost = await get_global_provider_cost_today(session)
    assert cost == 125.50

@pytest.mark.asyncio
async def test_get_client_provider_cost_today():
    session = AsyncMock()
    client_id = uuid4()
    mock_result = MagicMock()
    mock_result.scalar.return_value = 12.75
    session.execute.return_value = mock_result
    
    cost = await get_client_provider_cost_today(session, client_id)
    assert cost == 12.75

@pytest.mark.asyncio
async def test_is_cloud_blocked_by_guardrails_not_saas():
    session = AsyncMock()
    client_id = uuid4()
    
    with patch("app.services.billing.guardrails.settings") as mock_settings:
        mock_settings.deployment_mode = "appliance"
        blocked, reason = await is_cloud_blocked_by_guardrails(session, client_id)
        assert blocked is False

@pytest.mark.asyncio
async def test_is_cloud_blocked_by_guardrails_global_limit():
    session = AsyncMock()
    client_id = uuid4()
    
    with patch("app.services.billing.guardrails.settings") as mock_settings:
        mock_settings.deployment_mode = "saas"
        mock_settings.max_global_provider_cost_per_day_brl = 100.0
        
        with patch("app.services.billing.guardrails.get_global_provider_cost_today", return_value=150.0):
            blocked, reason = await is_cloud_blocked_by_guardrails(session, client_id)
            assert blocked is True
            assert "Global SaaS provider cost limit reached" in reason

@pytest.mark.asyncio
async def test_is_cloud_blocked_by_guardrails_client_limit():
    session = AsyncMock()
    client_id = uuid4()
    
    with patch("app.services.billing.guardrails.settings") as mock_settings:
        mock_settings.deployment_mode = "saas"
        mock_settings.max_global_provider_cost_per_day_brl = 1000.0
        mock_settings.max_client_provider_cost_per_day_brl = 10.0
        
        with patch("app.services.billing.guardrails.get_global_provider_cost_today", return_value=50.0):
            with patch("app.services.billing.guardrails.get_client_provider_cost_today", return_value=15.0):
                blocked, reason = await is_cloud_blocked_by_guardrails(session, client_id)
                assert blocked is True
                assert "Client daily provider cost limit reached" in reason

@pytest.mark.asyncio
async def test_is_cloud_blocked_by_guardrails_not_blocked():
    session = AsyncMock()
    client_id = uuid4()
    
    with patch("app.services.billing.guardrails.settings") as mock_settings:
        mock_settings.deployment_mode = "saas"
        mock_settings.max_global_provider_cost_per_day_brl = 1000.0
        mock_settings.max_client_provider_cost_per_day_brl = 100.0
        
        with patch("app.services.billing.guardrails.get_global_provider_cost_today", return_value=50.0):
            with patch("app.services.billing.guardrails.get_client_provider_cost_today", return_value=15.0):
                blocked, reason = await is_cloud_blocked_by_guardrails(session, client_id)
                assert blocked is False
