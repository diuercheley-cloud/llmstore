import pytest
from datetime import datetime, timedelta
from app.services.observability.base import ObservabilityMetric, MetricType, AnomalySeverity
from app.services.observability.anomaly_detector import AnomalyDetector
from app.services.observability.ebpf_collector import EBPFCollector
from app.services.observability.service import AdvancedObservabilityService


def test_anomaly_detector_detects_spike():
    detector = AnomalyDetector(z_threshold=2.0)
    metric_name = "test.latency"
    
    # 1. Fill history with baseline values
    for _ in range(15):
        detector.detect(ObservabilityMetric(
            name=metric_name, value=100.0, type=MetricType.GAUGE, unit="ms"
        ))
        
    # 2. Introduce a spike
    spike_metric = ObservabilityMetric(
        name=metric_name, value=500.0, type=MetricType.GAUGE, unit="ms"
    )
    anomaly = detector.detect(spike_metric)
    
    assert anomaly is not None
    assert anomaly.metric_name == metric_name
    assert anomaly.severity in [AnomalySeverity.MEDIUM, AnomalySeverity.HIGH]
    assert anomaly.value == 500.0


def test_ebpf_collector_status():
    collector = EBPFCollector()
    # Should not crash even if /sys/kernel/debug/tracing is missing
    status = collector.get_status()
    assert status in ["active", "unavailable"]


@pytest.mark.asyncio
async def test_observability_service_integration():
    service = AdvancedObservabilityService()
    
    # Run collection
    anomalies = await service.collect_and_analyze()
    
    assert isinstance(anomalies, list)
    summary = service.get_summary()
    assert "metrics_count" in summary
    assert "ebpf_available" in summary


def test_anomaly_detector_dry_run():
    detector = AnomalyDetector(z_threshold=2.0)
    values = [10.0] * 15 + [100.0]
    
    anomalies = detector.dry_run("test.metric", values)
    
    assert len(anomalies) > 0
    assert anomalies[0].value == 100.0
