from pathlib import Path
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.managed_metrics import update_managed_metrics
from app.services.compliance_readiness import ComplianceReadinessService
from app.services.model_experiments.experiment_metrics import ExperimentMetrics
from app.services.observability.anomaly_detector import AnomalyDetector
from app.services.observability.base import MetricType, ObservabilityMetric
from app.services.observability.ebpf_collector import EBPFCollector
from app.services.observability.otlp_exporter import OTLPExporter
from app.services.operations.disaster_recovery.backup_manifest_service import build_backup_hash
from app.services.operations.disaster_recovery.recovery_receipts import build_recovery_receipt
from app.services.operations.events.event_contract_registry import build_contract_hash
from app.services.operations.events.event_schema_compatibility import compatibility_status
from app.services.operations.observability.metric_recorder import build_metric_hash
from app.services.operations.observability.observability_replay_verifier import verify_metric_replay
from app.services.operations.observability.trace_recorder import build_trace_hash
from app.services.platform.release_artifact_resolver import ReleaseArtifactResolver


def test_deterministic_operational_hashes_and_compatibility(tmp_path: Path):
    assert build_backup_hash("c", "b", "full") == build_backup_hash("c", "b", "full")
    assert build_contract_hash("event", "1.0", "local", {}) == build_contract_hash("event", "1.0", "local", {})
    assert build_trace_hash("c", "trace", "local", "subject")
    assert build_recovery_receipt("plan-123456789012", "passed")["signature"].startswith("recovery_receipt_")
    assert compatibility_status("1.2.0", "1.9.0") == "compatible"
    assert compatibility_status("1.2.0", "2.0.0") == "breaking"

    resolver = ReleaseArtifactResolver(tmp_path)
    assert resolver.get_summary_path("v1") == tmp_path / "artifacts/releases/v1/summary.md"


def test_observability_services_fail_safe(monkeypatch):
    payload = {"client_id": "c", "metric_name": "latency", "metric_scope": "local", "metric_value": "1"}
    expected = build_metric_hash(**payload)
    assert verify_metric_replay(payload, expected)["replay_safe"] is True

    detector = AnomalyDetector()
    metric = ObservabilityMetric(name="latency", value=1, type=MetricType.GAUGE, unit="ms")
    for _ in range(10):
        assert detector.detect(metric) is None
    assert detector.detect(metric.model_copy(update={"value": 100})) is not None

    collector = EBPFCollector()
    collector._available = False
    assert collector.get_status() == "unavailable"

    monkeypatch.setattr("app.services.observability.otlp_exporter.get_settings", lambda: MagicMock(otlp_export_enabled=False))
    provider = MagicMock()
    OTLPExporter().setup(provider)
    provider.add_span_processor.assert_not_called()

    update_managed_metrics(1, 0, 1)


@pytest.mark.asyncio
async def test_experiment_metrics_empty_summary():
    result = MagicMock()
    result.mappings.return_value = []
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)

    summary = await ExperimentMetrics(db).get_summary(uuid.uuid4())

    assert summary["variants"] == {}


@pytest.mark.asyncio
async def test_compliance_readiness_score():
    framework = SimpleNamespace(
        name="SOC2",
        controls=[
            SimpleNamespace(status="implemented"),
            SimpleNamespace(status="partial"),
            SimpleNamespace(status="not_started"),
        ],
    )
    db = MagicMock()
    db.get = AsyncMock(return_value=framework)

    report = await ComplianceReadinessService(db).get_readiness_report("soc2")

    assert report["readiness_score"] == pytest.approx(0.5)
