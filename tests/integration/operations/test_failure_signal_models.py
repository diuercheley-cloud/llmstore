from app.core.time import utc_now
from app.models.operations.failure_signals import (
    FailureForecast,
    FailureRiskAssessment,
    FailureSignal,
    compute_deterministic_hash,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class TestComputeDeterministicHash:
    def test_deterministic_same_input(self):
        fields = {"client_id": "c1", "signal_type": "latency_spike", "value": 99.5}
        h1 = compute_deterministic_hash(fields=fields)
        h2 = compute_deterministic_hash(fields=fields)
        assert h1 == h2

    def test_deterministic_different_input(self):
        h1 = compute_deterministic_hash(fields={"a": 1})
        h2 = compute_deterministic_hash(fields={"a": 2})
        assert h1 != h2

    def test_deterministic_versioned(self):
        fields = {"client_id": "c1"}
        h_v1 = compute_deterministic_hash(fields=fields, version="v1")
        h_v2 = compute_deterministic_hash(fields=fields, version="v2")
        assert h_v1 != h_v2

    def test_output_format(self):
        h = compute_deterministic_hash(fields={"x": 1})
        assert isinstance(h, str)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


class TestFailureSignalModel:
    async def test_create_failure_signal(self, session: AsyncSession):
        now = utc_now()
        signal = FailureSignal(
            client_id="client-1",
            signal_type="latency_spike",
            source_domain="runtime",
            source_ref="node-42",
            severity="warning",
            confidence=0.85,
            observed_at=now,
            payload_json={"latency_ms": 5000, "threshold": 2000},
        )
        session.add(signal)
        await session.commit()

        result = await session.execute(
            select(FailureSignal).where(FailureSignal.client_id == "client-1")
        )
        saved = result.scalars().one()
        assert saved.signal_type == "latency_spike"
        assert saved.severity == "warning"
        assert saved.confidence == 0.85
        assert saved.source_domain == "runtime"
        assert saved.source_ref == "node-42"
        assert saved.payload_json == {"latency_ms": 5000, "threshold": 2000}
        assert saved.id is not None
        assert saved.created_at is not None

    async def test_failure_signal_default_severity(self, session: AsyncSession):
        now = utc_now()
        signal = FailureSignal(
            client_id="client-2",
            signal_type="cpu_throttle",
            source_domain="infra",
            observed_at=now,
        )
        session.add(signal)
        await session.commit()

        result = await session.execute(
            select(FailureSignal).where(FailureSignal.client_id == "client-2")
        )
        saved = result.scalars().one()
        assert saved.severity == "info"

    async def test_failure_signal_immutable_hash(self, session: AsyncSession):
        now = utc_now()
        signal = FailureSignal(
            client_id="client-3",
            signal_type="memory_pressure",
            source_domain="runtime",
            observed_at=now,
            immutable_hash="abc123",
            previous_hash="prevhash",
        )
        session.add(signal)
        await session.commit()

        result = await session.execute(
            select(FailureSignal).where(FailureSignal.client_id == "client-3")
        )
        saved = result.scalars().one()
        assert saved.immutable_hash == "abc123"
        assert saved.previous_hash == "prevhash"


class TestFailureForecastModel:
    async def test_create_forecast(self, session: AsyncSession):
        forecast = FailureForecast(
            client_id="client-1",
            forecast_type="node_failure",
            forecast_window_minutes=30,
            risk_score=0.72,
            confidence=0.88,
            deterministic_version="v1",
            input_hash="input123",
        )
        session.add(forecast)
        await session.commit()

        result = await session.execute(
            select(FailureForecast).where(FailureForecast.client_id == "client-1")
        )
        saved = result.scalars().one()
        assert saved.forecast_type == "node_failure"
        assert saved.forecast_window_minutes == 30
        assert saved.risk_score == 0.72
        assert saved.confidence == 0.88
        assert saved.deterministic_version == "v1"
        assert saved.input_hash == "input123"

    async def test_forecast_advisory_only_default_true(self, session: AsyncSession):
        forecast = FailureForecast(
            client_id="client-2",
            forecast_type="queue_saturation",
        )
        session.add(forecast)
        await session.commit()

        result = await session.execute(
            select(FailureForecast).where(FailureForecast.client_id == "client-2")
        )
        saved = result.scalars().one()
        assert saved.advisory_only is True

    async def test_forecast_advisory_only_explicit_false(self, session: AsyncSession):
        forecast = FailureForecast(
            client_id="client-3",
            forecast_type="quorum_loss",
            advisory_only=False,
        )
        session.add(forecast)
        await session.commit()

        result = await session.execute(
            select(FailureForecast).where(FailureForecast.client_id == "client-3")
        )
        saved = result.scalars().one()
        assert saved.advisory_only is False

    async def test_forecast_immutable_hash(self, session: AsyncSession):
        forecast = FailureForecast(
            client_id="client-4",
            forecast_type="thermal_throttle",
            immutable_hash="fixedhash",
        )
        session.add(forecast)
        await session.commit()

        result = await session.execute(
            select(FailureForecast).where(FailureForecast.client_id == "client-4")
        )
        saved = result.scalars().one()
        assert saved.immutable_hash == "fixedhash"


class TestFailureRiskAssessmentModel:
    async def test_create_risk_assessment(self, session: AsyncSession):
        assessment = FailureRiskAssessment(
            client_id="client-1",
            forecast_id="forecast-1",
            risk_level="high",
            recommendation="Isolate node for inspection",
            requires_approval=True,
        )
        session.add(assessment)
        await session.commit()

        result = await session.execute(
            select(FailureRiskAssessment).where(FailureRiskAssessment.client_id == "client-1")
        )
        saved = result.scalars().one()
        assert saved.risk_level == "high"
        assert saved.recommendation == "Isolate node for inspection"
        assert saved.requires_approval is True

    async def test_risk_assessment_defaults(self, session: AsyncSession):
        assessment = FailureRiskAssessment(
            client_id="client-2",
        )
        session.add(assessment)
        await session.commit()

        result = await session.execute(
            select(FailureRiskAssessment).where(FailureRiskAssessment.client_id == "client-2")
        )
        saved = result.scalars().one()
        assert saved.risk_level == "low"
        assert saved.advisory_only is True
        assert saved.dry_run is True
        assert saved.requires_approval is False
        assert saved.recommendation is None
