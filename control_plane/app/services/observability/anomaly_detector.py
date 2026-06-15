import logging

from app.services.observability.base import Anomaly, AnomalySeverity, ObservabilityMetric

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """
    Deterministic anomaly detection using rolling Z-score.
    """

    def __init__(self, z_threshold: float = 3.0):
        self.z_threshold = z_threshold
        # In-memory history for baseline calculation (should be persisted in production)
        self.history: dict[str, list[float]] = {}

    def detect(self, metric: ObservabilityMetric) -> Anomaly | None:
        name = metric.name
        val = metric.value

        if name not in self.history:
            self.history[name] = []

        history = self.history[name]

        if len(history) < 10:
            history.append(val)
            return None

        # Calculate mean and standard deviation
        avg = sum(history) / len(history)
        variance = sum((x - avg) ** 2 for x in history) / len(history)
        std_dev = variance**0.5

        history.append(val)
        if len(history) > 100:
            history.pop(0)

        if std_dev == 0:
            # If standard deviation is zero but value changed significantly, it's an anomaly
            if abs(val - avg) > 0.0001:
                z_score = float("inf")
            else:
                return None
        else:
            z_score = abs(val - avg) / std_dev

        if z_score > self.z_threshold:
            severity = AnomalySeverity.HIGH if z_score > 5.0 else AnomalySeverity.MEDIUM

            return Anomaly(
                metric_name=name,
                severity=severity,
                description=f"Spike detected in {name}. Current: {val}, Baseline: {avg:.2f}",
                value=val,
                baseline=avg,
                evidence={"z_score": z_score, "history_len": len(history)},
            )

        return None

    def dry_run(self, metric_name: str, values: list[float]) -> list[Anomaly]:
        """Simulation mode to test thresholds."""
        anomalies = []
        # Clear temporary history for dry-run
        temp_history = []

        for v in values:
            mock_metric = ObservabilityMetric(name=metric_name, value=v, type="gauge", unit="unit")

            # Simple simulation logic
            if len(temp_history) >= 10:
                avg = sum(temp_history) / len(temp_history)
                std = (sum((x - avg) ** 2 for x in temp_history) / len(temp_history)) ** 0.5

                z = 0.0
                if std == 0:
                    z = float("inf") if abs(v - avg) > 0.0001 else 0.0
                else:
                    z = abs(v - avg) / std

                if z > self.z_threshold:
                    anomalies.append(
                        Anomaly(
                            metric_name=metric_name,
                            severity=AnomalySeverity.MEDIUM,
                            description=f"Dry-run detection at value {v}",
                            value=v,
                            baseline=avg,
                        )
                    )
            temp_history.append(v)

        return anomalies
