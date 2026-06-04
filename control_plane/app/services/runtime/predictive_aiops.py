import hashlib
import logging
from datetime import datetime
from typing import Any, List

from app.models.commercial_predictive_aiops import (
    CommercialAIOpsRecommendation,
    CommercialAnomalySignal,
    CommercialFailurePrediction,
    CommercialRuntimeRiskTrend,
)
from app.services.runtime.anomaly_correlation import AnomalyCorrelator
from app.services.runtime.failure_forecasting import FailureForecaster
from app.services.runtime.runtime_risk_scoring import RuntimeRiskScorer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class PredictiveAIOpsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.forecaster = FailureForecaster(db)
        self.correlator = AnomalyCorrelator(db)
        self.risk_scorer = RuntimeRiskScorer(db)

    async def run_cycle(self, client_id: str = "system"):
        """Runs a full AIOps cycle: anomaly detection -> failure forecasting -> risk scoring -> recommendations"""
        logger.info(f"Running AIOps cycle for client {client_id}")
        
        # 1. Detect and Correlate Anomalies
        anomalies = await self.correlator.process_latest_metrics(client_id)
        
        # 2. Forecast Failures
        forecasts = await self.forecaster.generate_forecasts(client_id, anomalies)
        
        # 3. Score Runtime Risk
        risk_trends = await self.risk_scorer.update_risk_trends(client_id, anomalies, forecasts)
        
        # 4. Generate Recommendations
        recommendations = await self.generate_recommendations(client_id, forecasts, risk_trends)
        
        return {
            "anomalies_detected": len(anomalies),
            "forecasts_generated": len(forecasts),
            "risk_trends_updated": len(risk_trends),
            "recommendations_generated": len(recommendations)
        }

    async def generate_recommendations(self, client_id: str, forecasts: List[Any], risk_trends: List[Any]) -> List[CommercialAIOpsRecommendation]:
        recommendations = []
        
        for forecast in forecasts:
            if forecast.confidence_score > 0.8:
                rec = CommercialAIOpsRecommendation(
                    client_id=client_id,
                    action_type=self._map_forecast_to_action(forecast),
                    target_id=forecast.target_id,
                    priority="high" if forecast.predicted_failure_window_seconds < 3600 else "medium",
                    rationale={
                        "forecast_id": forecast.id,
                        "confidence": forecast.confidence_score,
                        "window": forecast.predicted_failure_window_seconds
                    },
                    mode="advisory",
                    status="pending"
                )
                rec.deterministic_hash = self._generate_hash(rec)
                rec.immutable_hash = rec.deterministic_hash
                self.db.add(rec)
                recommendations.append(rec)
        
        await self.db.commit()
        return recommendations

    def _map_forecast_to_action(self, forecast):
        mapping = {
            "queue_saturation": "throttle_tenant",
            "node_failure": "isolate_node",
            "quorum_loss": "resync_mesh",
            "gpu_thermal": "quarantine_model",
            "drift_detected": "replay_workflow"
        }
        return mapping.get(forecast.prediction_type, "enable_safe_mode")

    def _generate_hash(self, obj):
        data = f"{obj.client_id}-{obj.action_type}-{obj.target_id}-{datetime.utcnow().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()

    async def get_status(self):
        return {
            "status": "active",
            "mode": "sovereign_local",
            "last_cycle": datetime.utcnow().isoformat(),
            "engine": "local_heuristics_v1"
        }

    async def get_latest_forecasts(self, limit: int = 50):
        stmt = select(CommercialFailurePrediction).order_by(CommercialFailurePrediction.created_at.desc()).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_latest_anomalies(self, limit: int = 50):
        stmt = select(CommercialAnomalySignal).order_by(CommercialAnomalySignal.created_at.desc()).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_latest_recommendations(self, limit: int = 50):
        stmt = select(CommercialAIOpsRecommendation).order_by(CommercialAIOpsRecommendation.created_at.desc()).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_risk_trends(self, limit: int = 50):
        stmt = select(CommercialRuntimeRiskTrend).order_by(CommercialRuntimeRiskTrend.created_at.desc()).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()
