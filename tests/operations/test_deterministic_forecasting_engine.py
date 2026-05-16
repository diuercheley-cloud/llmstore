from datetime import datetime, timedelta, timezone

from app.services.operations.forecasting.deterministic_engine import (
    DeterministicFailureForecastingEngine,
)

T0 = datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc)
ENGINE = DeterministicFailureForecastingEngine()


def _signal(**kw):
    defaults = dict(
        signal_type="latency_spike",
        source_domain="runtime",
        severity="warning",
        confidence=0.7,
        observed_at=T0,
    )
    defaults.update(kw)
    return defaults


# ── Determinism ──────────────────────────────────────────────────────────────


class TestDeterminism:

    def test_same_input_produces_same_output(self):
        sigs = [
            _signal(signal_type="latency_spike", severity="critical"),
            _signal(signal_type="memory_pressure", source_domain="infra"),
        ]
        f1 = ENGINE.forecast(sigs)
        f2 = ENGINE.forecast(sigs)
        assert f1 == f2

    def test_determinism_across_multiple_calls(self):
        sigs = [_signal() for _ in range(5)]
        results = [ENGINE.forecast(sigs) for _ in range(10)]
        for r in results:
            assert r == results[0]

    def test_normalize_is_deterministic(self):
        sigs = [_signal(signal_type="cpu", severity="critical")]
        n1 = ENGINE.normalize_signals(sigs)
        n2 = ENGINE.normalize_signals(sigs)
        assert n1 == n2

    def test_input_hash_is_deterministic(self):
        sigs = [_signal(signal_type="cpu_throttle")]
        h1 = ENGINE.compute_input_hash(sigs)
        h2 = ENGINE.compute_input_hash(sigs)
        assert h1 == h2


# ── No mutation ──────────────────────────────────────────────────────────────


class TestNoMutation:

    def test_normalize_does_not_mutate_original(self):
        original = [{"signal_type": "latency", "source_domain": "runtime", "severity": "critical", "confidence": 0.9, "observed_at": T0}]
        copy_before = list(original)
        ENGINE.normalize_signals(original)
        assert original == copy_before

    def test_forecast_does_not_mutate_signals(self):
        sigs = [_signal()]
        copy_before = [dict(s) for s in sigs]
        ENGINE.forecast(sigs)
        assert sigs == copy_before


# ── Zero risk without signals ────────────────────────────────────────────────


class TestZeroRisk:

    def test_empty_signals_returns_zero_risk(self):
        f = ENGINE.forecast([])
        assert f["risk_score"] == 0.0
        assert f["advisory_only"] is True

    def test_empty_signals_confidence_is_one(self):
        f = ENGINE.forecast([])
        assert f["confidence"] == 1.0

    def test_empty_signals_explanation(self):
        f = ENGINE.forecast([])
        assert "No signals provided" in f["explanation"]["note"]


# ── Severity drives risk ─────────────────────────────────────────────────────


class TestSeverityDrivesRisk:

    def test_info_lowest_risk(self):
        f = ENGINE.forecast([_signal(severity="info")])
        assert f["risk_score"] > 0.0

    def test_critical_higher_than_warning(self):
        f_low = ENGINE.forecast([_signal(severity="warning")])
        f_high = ENGINE.forecast([_signal(severity="critical")])
        assert f_high["risk_score"] > f_low["risk_score"]

    def test_warning_higher_than_info(self):
        f_info = ENGINE.forecast([_signal(severity="info")])
        f_warn = ENGINE.forecast([_signal(severity="warning")])
        assert f_warn["risk_score"] > f_info["risk_score"]

    def test_error_between_warning_and_critical(self):
        f_warn = ENGINE.forecast([_signal(severity="warning")])
        f_err = ENGINE.forecast([_signal(severity="error")])
        f_crit = ENGINE.forecast([_signal(severity="critical")])
        assert f_warn["risk_score"] < f_err["risk_score"] < f_crit["risk_score"]


# ── Input hash stability ─────────────────────────────────────────────────────


class TestInputHash:

    def test_hash_stable_for_same_signals(self):
        sigs = [
            _signal(signal_type="cpu", severity="info"),
            _signal(signal_type="mem", severity="critical"),
        ]
        h = ENGINE.compute_input_hash(sigs)
        assert isinstance(h, str)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_hash_changes_when_signal_changes(self):
        sigs_a = [_signal(signal_type="cpu", severity="info")]
        sigs_b = [_signal(signal_type="cpu", severity="critical")]
        assert ENGINE.compute_input_hash(sigs_a) != ENGINE.compute_input_hash(sigs_b)

    def test_hash_changes_when_fields_change(self):
        sigs_a = [_signal(signal_type="cpu")]
        sigs_b = [_signal(signal_type="memory")]
        assert ENGINE.compute_input_hash(sigs_a) != ENGINE.compute_input_hash(sigs_b)

    def test_hash_changes_with_additional_signal(self):
        sigs_a = [_signal(signal_type="cpu")]
        sigs_b = [_signal(signal_type="cpu"), _signal(signal_type="memory")]
        assert ENGINE.compute_input_hash(sigs_a) != ENGINE.compute_input_hash(sigs_b)


# ── Heuristic: recency ───────────────────────────────────────────────────────


class TestRecencyHeuristic:

    def test_recent_signals_boost_risk(self):
        recent = T0 - timedelta(minutes=5)
        old = T0 - timedelta(minutes=120)

        f_recent = ENGINE.forecast(
            [_signal(signal_type="cpu", severity="critical", observed_at=recent)],
            window_minutes=60,
            reference_time=T0,
        )
        f_old = ENGINE.forecast(
            [_signal(signal_type="cpu", severity="critical", observed_at=old)],
            window_minutes=60,
            reference_time=T0,
        )
        assert f_recent["risk_score"] > f_old["risk_score"]


# ── Heuristic: repetition ────────────────────────────────────────────────────


class TestRepetitionHeuristic:

    def test_repeated_signals_increase_risk(self):
        one = [_signal(signal_type="cpu", severity="warning")]
        many = [
            _signal(signal_type="cpu", severity="warning"),
            _signal(signal_type="cpu", severity="warning"),
            _signal(signal_type="cpu", severity="warning"),
        ]
        f_one = ENGINE.forecast(one)
        f_many = ENGINE.forecast(many)
        assert f_many["risk_score"] > f_one["risk_score"]

    def test_repetition_factor_capped_at_2(self):
        sigs = [_signal(signal_type="same", severity="info") for _ in range(20)]
        f = ENGINE.forecast(sigs)
        assert f["risk_score"] <= 1.0


# ── Heuristic: domain diversity increases confidence ─────────────────────────


class TestDomainDiversity:

    def test_more_domains_increase_confidence(self):
        single = [
            _signal(signal_type="cpu", source_domain="runtime"),
        ]
        multi = [
            _signal(signal_type="cpu", source_domain="runtime"),
            _signal(signal_type="mem", source_domain="infra"),
            _signal(signal_type="net", source_domain="network"),
        ]
        f_single = ENGINE.forecast(single)
        f_multi = ENGINE.forecast(multi)
        assert f_multi["confidence"] > f_single["confidence"]

    def test_confidence_never_exceeds_0_95(self):
        many_domains = [
            _signal(signal_type=f"t{i}", source_domain=f"domain{i}")
            for i in range(20)
        ]
        f = ENGINE.forecast(many_domains)
        assert f["confidence"] <= 0.95


# ── Output contract ──────────────────────────────────────────────────────────


class TestOutputContract:

    def test_forecast_contains_all_required_keys(self):
        f = ENGINE.forecast([_signal()])
        assert "forecast_type" in f
        assert "risk_score" in f
        assert "confidence" in f
        assert "deterministic_version" in f
        assert "input_hash" in f
        assert "explanation" in f
        assert "advisory_only" in f

    def test_advisory_only_is_true(self):
        f = ENGINE.forecast([_signal()])
        assert f["advisory_only"] is True

    def test_deterministic_version(self):
        f = ENGINE.forecast([_signal()])
        assert f["deterministic_version"] == "v1"

    def test_risk_score_range(self):
        f = ENGINE.forecast([_signal(severity="critical")])
        assert 0.0 <= f["risk_score"] <= 1.0

    def test_confidence_range(self):
        f = ENGINE.forecast([_signal(severity="critical")])
        assert 0.0 <= f["confidence"] <= 1.0

    def test_forecast_type_default(self):
        f = ENGINE.forecast([_signal()])
        assert f["forecast_type"] == "aggregate_failure_risk"

    def test_forecast_type_custom(self):
        f = ENGINE.forecast([_signal()], forecast_type="node_failure")
        assert f["forecast_type"] == "node_failure"


# ── Explain ──────────────────────────────────────────────────────────────────


class TestExplain:

    def test_explain_zero_risk(self):
        f = ENGINE.forecast([])
        text = ENGINE.explain_forecast(f)
        assert "zero risk" in text.lower() or "0.0" in text

    def test_explain_contains_risk_score(self):
        f = ENGINE.forecast([_signal(severity="critical")])
        text = ENGINE.explain_forecast(f)
        assert str(f["risk_score"]) in text

    def test_explain_contains_input_hash(self):
        f = ENGINE.forecast([_signal()])
        text = ENGINE.explain_forecast(f)
        assert f["input_hash"] in text


# ── Edge cases ───────────────────────────────────────────────────────────────


class TestEdgeCases:

    def test_missing_fields_do_not_crash(self):
        sigs = [{}]
        f = ENGINE.forecast(sigs)
        assert 0.0 <= f["risk_score"] <= 1.0
        assert 0.0 <= f["confidence"] <= 1.0

    def test_partial_fields(self):
        sigs = [{"signal_type": "cpu"}]
        f = ENGINE.forecast(sigs)
        assert 0.0 <= f["risk_score"] <= 1.0
        assert f["advisory_only"] is True

    def test_explicit_reference_time(self):
        custom_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
        f = ENGINE.forecast(
            [_signal(observed_at=T0)],
            reference_time=custom_time,
        )
        assert 0.0 <= f["risk_score"] <= 1.0

    def test_forecast_with_no_timestamps(self):
        sigs = [
            {"signal_type": "cpu", "source_domain": "runtime", "severity": "warning", "confidence": 0.5},
        ]
        f = ENGINE.forecast(sigs)
        assert f["risk_score"] > 0.0

    def test_normalize_with_unexpected_fields(self):
        sigs = [{"unexpected": True, "signal_type": "cpu"}]
        n = ENGINE.normalize_signals(sigs)
        assert n[0]["signal_type"] == "cpu"
        assert n[0]["source_domain"] == "unknown"
