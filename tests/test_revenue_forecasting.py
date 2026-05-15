import pytest
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from app.services.billing.revenue_forecasting import RevenueForecastingService
from app.models.commercial_revenue_forecast import CommercialRevenueForecast
from app.models.request_financial import RequestFinancial


@pytest.mark.asyncio
async def test_forecast_empty_data():
    session = AsyncMock()
    # Mock return empty for historical series
    mock_result = MagicMock()
    mock_result.all.return_value = []
    session.execute.return_value = mock_result
    
    svc = RevenueForecastingService(session)
    forecast = await svc.forecast_revenue(window_days=30)
    
    assert forecast.predicted_amount_brl == Decimal("0.00")
    assert forecast.confidence == "low"


@pytest.mark.asyncio
async def test_forecast_moving_average():
    session = AsyncMock()
    # Mock 10 days of stable data INCLUDING today
    rows = []
    base_date = datetime.now() - timedelta(days=9)
    for i in range(10):
        row = MagicMock()
        row.day = base_date + timedelta(days=i)
        row.val = Decimal("100.00")
        rows.append(row)
    
    mock_result = MagicMock()
    mock_result.all.return_value = rows
    session.execute.return_value = mock_result
    
    svc = RevenueForecastingService(session)
    forecast = await svc.forecast_revenue(window_days=30, method="moving_average")
    
    # 100/day * 30 days = 3000
    assert float(forecast.predicted_amount_brl) == 3000.0


@pytest.mark.asyncio
async def test_forecast_linear_trend():
    session = AsyncMock()
    # Mock 30 days of growing data
    rows = []
    base_date = datetime.now() - timedelta(days=29)
    for i in range(1, 31):
        row = MagicMock()
        row.day = base_date + timedelta(days=i-1)
        row.val = Decimal(str(i * 10))
        rows.append(row)
    
    mock_result = MagicMock()
    mock_result.all.return_value = rows
    session.execute.return_value = mock_result
    
    svc = RevenueForecastingService(session)
    forecast = await svc.forecast_revenue(window_days=7, method="linear_trend")
    
    # Day 30 is 300. Slope is 10.
    # Day 31: 310, ..., Day 37: 370.
    # Sum: 310+320+330+340+350+360+370 = 2380
    assert float(forecast.predicted_amount_brl) >= 2000.0
