import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.governance.governance_risk_engine import GovernanceRiskEngine

@pytest.mark.asyncio
async def test_calculate_risk(session: AsyncSession):
    engine = GovernanceRiskEngine(session)
    score = await engine.calculate_risk()
    
    assert score is not None
    assert score.overall_risk_score > 0
    assert score.financial_risk > 0
    assert "anomalies_detected" in score.risk_factors
