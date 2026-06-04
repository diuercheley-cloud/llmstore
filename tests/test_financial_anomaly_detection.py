from unittest.mock import AsyncMock, MagicMock

import pytest
from app.services.billing.financial_anomaly_detection import FinancialAnomalyDetectionService


@pytest.mark.asyncio
async def test_detect_revenue_spike():
    session = AsyncMock()
    
    # Baseline: 10 days of 100.00
    mock_result_hist = MagicMock()
    mock_result_hist.all.return_value = [ (100.0,) ] * 10
    
    # Recent: 500.00 (spike!)
    mock_result_recent = MagicMock()
    mock_result_recent.scalar.return_value = 500.0
    
    session.execute.side_effect = [mock_result_hist, mock_result_recent, AsyncMock()]
    
    svc = FinancialAnomalyDetectionService(session)
    anomalies = await svc.detect_revenue_anomalies()
    
    assert len(anomalies) == 1
    assert anomalies[0].anomaly_type == "revenue_spike"
    assert anomalies[0].severity in ["high", "critical"]
    assert float(anomalies[0].observed_value_brl) == 500.0


@pytest.mark.asyncio
async def test_detect_margin_drop():
    session = AsyncMock()
    
    # Baseline: 10 days of 50.00 margin
    mock_result_hist = MagicMock()
    mock_result_hist.all.return_value = [ (50.0,) ] * 10
    
    # Recent: 5.00 margin (drop!)
    mock_result_recent = MagicMock()
    mock_result_recent.scalar.return_value = 5.0
    
    session.execute.side_effect = [mock_result_hist, mock_result_recent, AsyncMock()]
    
    svc = FinancialAnomalyDetectionService(session)
    anomalies = await svc.detect_margin_anomalies()
    
    assert len(anomalies) == 1
    assert anomalies[0].anomaly_type == "margin_drop"
    assert anomalies[0].severity in ["high", "critical"]


@pytest.mark.asyncio
async def test_summarize_anomalies():
    session = AsyncMock()
    
    row1 = MagicMock()
    row1.status = "open"
    row1.__getitem__.return_value = 5
    
    row2 = MagicMock()
    row2.status = "resolved"
    row2.__getitem__.return_value = 2
    
    mock_result_sum = MagicMock()
    mock_result_sum.all.return_value = [row1, row2]
    
    mock_result_crit = MagicMock()
    mock_result_crit.scalar.return_value = 1 # 1 critical open
    
    session.execute.side_effect = [mock_result_sum, mock_result_crit]
    
    svc = FinancialAnomalyDetectionService(session)
    summary = await svc.summarize_anomalies()
    
    assert summary["open"] == 5
    assert summary["resolved"] == 2
    assert summary["critical_open"] == 1
