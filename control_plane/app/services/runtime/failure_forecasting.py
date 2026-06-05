import hashlib
import logging
from datetime import datetime, UTC
from typing import Any, List, Optional

from app.models.commercial_predictive_aiops import (
    CommercialFailurePrediction,
)
from app.models.commercial_runtime_fabric import CommercialRuntimeFabricHealth
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class FailureForecaster:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_forecasts(self, client_id: str, anomalies: List[Any]) -> List[CommercialFailurePrediction]:
        forecasts = []
        
        # 1. Analyze node health trends
        stmt = select(CommercialRuntimeFabricHealth)
        result = await self.db.execute(stmt)
        nodes = result.scalars().all()
        
        for node in nodes:
            forecast = self._analyze_node_trend(node)
            if forecast:
                forecast.client_id = client_id
                self.db.add(forecast)
                forecasts.append(forecast)
        
        # 2. Analyze anomaly clusters
        cluster_forecasts = self._analyze_anomaly_clusters(client_id, anomalies)
        for cf in cluster_forecasts:
            self.db.add(cf)
            forecasts.append(cf)
        
        await self.db.commit()
        return forecasts

    def _analyze_node_trend(self, node: CommercialRuntimeFabricHealth) -> Optional[CommercialFailurePrediction]:
        metrics = node.metrics or {}
        cpu = metrics.get("cpu", 0)
        mem = metrics.get("mem", 0)
        
        if cpu > 90 or mem > 90:
            return CommercialFailurePrediction(
                target_id=node.node_id,
                prediction_type="node_failure",
                confidence_score=0.85,
                predicted_failure_window_seconds=1800,
                details={"cpu": cpu, "mem": mem, "reason": "resource_exhaustion"},
                deterministic_hash=hashlib.sha256(f"node-{node.node_id}-{datetime.now(UTC).isoformat()}".encode()).hexdigest()
            )
        return None

    def _analyze_anomaly_clusters(self, client_id: str, anomalies: List[Any]) -> List[CommercialFailurePrediction]:
        gpu_anomalies = [a for a in anomalies if a.anomaly_type in ["thermal", "power"]]
        if len(gpu_anomalies) >= 3:
            return [CommercialFailurePrediction(
                client_id=client_id,
                target_id="gpu_cluster_0",
                prediction_type="gpu_thermal",
                confidence_score=0.92,
                predicted_failure_window_seconds=900,
                details={"anomaly_count": len(gpu_anomalies)},
                deterministic_hash=hashlib.sha256(f"gpu-{client_id}-{datetime.now(UTC).isoformat()}".encode()).hexdigest()
            )]
        return []
