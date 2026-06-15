import logging
from typing import Any

from app.services.observability.anomaly_detector import AnomalyDetector
from app.services.observability.base import Anomaly, ObservabilityMetric
from app.services.observability.ebpf_collector import EBPFCollector

logger = logging.getLogger(__name__)


class AdvancedObservabilityService:
    def __init__(self):
        self.ebpf = EBPFCollector()
        self.detector = AnomalyDetector()
        self.recent_metrics: list[ObservabilityMetric] = []
        self.recent_anomalies: list[Anomaly] = []

    async def collect_and_analyze(self) -> list[Anomaly]:
        # 1. Collect standard metrics (Simulated here)
        standard_metrics = [
            ObservabilityMetric(name="inference.latency", value=450.0, type="gauge", unit="ms"),
            ObservabilityMetric(
                name="agent.token_usage", value=1200.0, type="counter", unit="tokens"
            ),
            ObservabilityMetric(name="system.error_rate", value=0.02, type="gauge", unit="ratio"),
        ]

        # 2. Collect eBPF metrics if available
        ebpf_metrics = await self.ebpf.collect_kernel_metrics()

        all_metrics = standard_metrics + ebpf_metrics
        self.recent_metrics = all_metrics

        # 3. Detect anomalies
        new_anomalies = []
        for m in all_metrics:
            anomaly = self.detector.detect(m)
            if anomaly:
                new_anomalies.append(anomaly)
                self.recent_anomalies.append(anomaly)

        if len(self.recent_anomalies) > 50:
            self.recent_anomalies = self.recent_anomalies[-50:]

        return new_anomalies

    def get_ebpf_status(self) -> str:
        return self.ebpf.get_status()

    def get_summary(self) -> dict[str, Any]:
        return {
            "ebpf_available": self.ebpf.is_available(),
            "metrics_count": len(self.recent_metrics),
            "anomalies_detected": len(self.recent_anomalies),
            "critical_anomalies": len(
                [a for a in self.recent_anomalies if a.severity == "critical"]
            ),
        }
