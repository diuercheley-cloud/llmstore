import hashlib
import logging
from datetime import UTC, datetime
from typing import Any

from app.models.commercial.commercial_predictive_aiops import CommercialRuntimeRiskTrend
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class RuntimeRiskScorer:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def update_risk_trends(
        self, client_id: str, anomalies: list[Any], forecasts: list[Any]
    ) -> list[CommercialRuntimeRiskTrend]:
        trends = []

        # Operational Risk
        op_risk_score = self._calculate_risk(anomalies, forecasts)
        trend = CommercialRuntimeRiskTrend(
            client_id=client_id,
            risk_type="operational",
            risk_score=op_risk_score,
            trend_direction="up" if op_risk_score > 0.5 else "stable",
            contributing_events={"anomalies": len(anomalies), "forecasts": len(forecasts)},
            deterministic_hash=hashlib.sha256(
                f"risk-{client_id}-{datetime.now(UTC).isoformat()}".encode()
            ).hexdigest(),
        )
        self.db.add(trend)
        trends.append(trend)

        await self.db.commit()
        return trends

    def _calculate_risk(self, anomalies, forecasts):
        score = 0.0
        score += len(anomalies) * 0.1
        score += len(forecasts) * 0.2
        return min(1.0, score)
