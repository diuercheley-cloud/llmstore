import hashlib
import logging
from datetime import datetime, timedelta, UTC
from typing import List

from app.models.commercial.commercial_predictive_aiops import CommercialAnomalySignal
from app.models.commercial.commercial_runtime_fabric import CommercialRuntimeFabricEvent
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class AnomalyCorrelator:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def process_latest_metrics(self, client_id: str) -> List[CommercialAnomalySignal]:
        anomalies = []
        
        # 1. Check for drift in runtime events
        stmt = select(CommercialRuntimeFabricEvent).filter(
            CommercialRuntimeFabricEvent.event_type == "drift_detected",
            CommercialRuntimeFabricEvent.created_at >= datetime.now(UTC) - timedelta(minutes=10)
        )
        result = await self.db.execute(stmt)
        drift_events = result.scalars().all()
        
        for event in drift_events:
            anomaly = CommercialAnomalySignal(
                client_id=client_id,
                source_id=event.source_node_id,
                anomaly_type="drift",
                severity="warning",
                drift_probability=0.75,
                metrics_snapshot=event.details,
                deterministic_hash=hashlib.sha256(f"drift-{event.id}".encode()).hexdigest()
            )
            self.db.add(anomaly)
            anomalies.append(anomaly)
            
        await self.db.commit()
        return anomalies
