from app.services.operations.forecasting.risk_scoring import (
    FailureRiskScoringService,
    RISK_THRESHOLDS,
    FALLBACK_LEVEL,
    ADVISORY_RECOMMENDATIONS,
    ADVISORY_REQUIRES_APPROVAL,
)

SERVICE = FailureRiskScoringService()


# ── classify_risk ────────────────────────────────────────────────────────────


class TestClassifyRisk:

    def test_zero_is_low(self):
        assert SERVICE.classify_risk(0.0) == "low"

    def test_below_threshold_is_low(self):
        assert SERVICE.classify_risk(0.24) == "low"
        assert SERVICE.classify_risk(0.1) == "low"
        assert SERVICE.classify_risk(0.01) == "low"

    def test_exactly_0_25_is_medium(self):
        assert SERVICE.classify_risk(0.25) == "medium"

    def test_medium_range(self):
        assert SERVICE.classify_risk(0.3) == "medium"
        assert SERVICE.classify_risk(0.49) == "medium"

    def test_exactly_0_5_is_high(self):
        assert SERVICE.classify_risk(0.5) == "high"

    def test_high_range(self):
        assert SERVICE.classify_risk(0.6) == "high"
        assert SERVICE.classify_risk(0.74) == "high"

    def test_exactly_0_75_is_critical(self):
        assert SERVICE.classify_risk(0.75) == "critical"

    def test_critical_range(self):
        assert SERVICE.classify_risk(0.8) == "critical"
        assert SERVICE.classify_risk(0.99) == "critical"
        assert SERVICE.classify_risk(1.0) == "critical"

    def test_above_one_clamps_to_critical(self):
        assert SERVICE.classify_risk(1.5) == "critical"

    def test_negative_score_returns_low(self):
        assert SERVICE.classify_risk(-0.1) == "low"

    def test_none_returns_low(self):
        assert SERVICE.classify_risk(None) == "low"  # type: ignore[arg-type]

    def test_string_returns_low(self):
        assert SERVICE.classify_risk("invalid") == "low"  # type: ignore[arg-type]

    def test_all_levels_exist_in_thresholds(self):
        levels = {level for _, level in RISK_THRESHOLDS}
        levels.add(FALLBACK_LEVEL)
        assert levels == {"low", "medium", "high", "critical"}


# ── recommendation_for_level ────────────────────────────────────────────────


class TestRecommendationForLevel:

    def test_low_recommendation(self):
        rec = SERVICE.recommendation_for_level("low")
        assert isinstance(rec, str)
        assert len(rec) > 0

    def test_medium_recommendation(self):
        rec = SERVICE.recommendation_for_level("medium")
        assert "investigation" in rec.lower() or "review" in rec.lower()

    def test_high_recommendation(self):
        rec = SERVICE.recommendation_for_level("high")
        assert "approval" in rec.lower()

    def test_critical_recommendation(self):
        rec = SERVICE.recommendation_for_level("critical")
        assert "approval" in rec.lower()
        assert "auto-remediate" in rec.lower()

    def test_invalid_level_falls_back_to_low(self):
        rec = SERVICE.recommendation_for_level("unknown")
        assert rec == ADVISORY_RECOMMENDATIONS["low"]

    def test_none_level_falls_back_to_low(self):
        rec = SERVICE.recommendation_for_level(None)  # type: ignore[arg-type]
        assert rec == ADVISORY_RECOMMENDATIONS["low"]

    def test_case_insensitive(self):
        assert SERVICE.recommendation_for_level("HIGH") == ADVISORY_RECOMMENDATIONS["high"]
        assert SERVICE.recommendation_for_level("Critical") == ADVISORY_RECOMMENDATIONS["critical"]

    def test_recommendation_is_sanitized(self):
        for level in ("low", "medium", "high", "critical"):
            rec = SERVICE.recommendation_for_level(level)
            assert "<script>" not in rec
            assert "<" not in rec

    def test_all_levels_have_recommendation(self):
        for level in ("low", "medium", "high", "critical"):
            rec = SERVICE.recommendation_for_level(level)
            assert isinstance(rec, str)
            assert len(rec) > 10


# ── requires_approval mapping ────────────────────────────────────────────────


class TestRequiresApproval:

    def test_low_does_not_require_approval(self):
        assert ADVISORY_REQUIRES_APPROVAL["low"] is False

    def test_medium_does_not_require_approval(self):
        assert ADVISORY_REQUIRES_APPROVAL["medium"] is False

    def test_high_requires_approval(self):
        assert ADVISORY_REQUIRES_APPROVAL["high"] is True

    def test_critical_requires_approval(self):
        assert ADVISORY_REQUIRES_APPROVAL["critical"] is True

    def test_build_assessment_maps_requires_approval_low(self):
        a = SERVICE.build_assessment({"risk_score": 0.1})
        assert a["requires_approval"] is False

    def test_build_assessment_maps_requires_approval_critical(self):
        a = SERVICE.build_assessment({"risk_score": 0.9})
        assert a["requires_approval"] is True


# ── build_assessment ────────────────────────────────────────────────────────


class TestBuildAssessment:

    MIN_FORECAST = {"risk_score": 0.3}

    def test_output_contains_all_required_keys(self):
        a = SERVICE.build_assessment(self.MIN_FORECAST)
        assert "risk_level" in a
        assert "risk_score" in a
        assert "recommendation" in a
        assert "requires_approval" in a
        assert "dry_run" in a
        assert "advisory_only" in a
        assert "immutable_hash" in a
        assert "deterministic_version" in a
        assert "input_hash" in a

    def test_advisory_only_is_always_true(self):
        a1 = SERVICE.build_assessment({"risk_score": 0.0})
        a2 = SERVICE.build_assessment({"risk_score": 0.9})
        assert a1["advisory_only"] is True
        assert a2["advisory_only"] is True

    def test_dry_run_defaults_to_true(self):
        a = SERVICE.build_assessment({"risk_score": 0.5})
        assert a["dry_run"] is True

    def test_dry_run_can_be_set_false(self):
        a = SERVICE.build_assessment({"risk_score": 0.5}, dry_run=False)
        assert a["dry_run"] is False

    def test_risk_level_matches_score(self):
        a = SERVICE.build_assessment({"risk_score": 0.1})
        assert a["risk_level"] == "low"
        a = SERVICE.build_assessment({"risk_score": 0.6})
        assert a["risk_level"] == "high"

    def test_immutable_hash_is_present(self):
        a = SERVICE.build_assessment(self.MIN_FORECAST)
        h = a["immutable_hash"]
        assert isinstance(h, str)
        assert len(h) == 64

    def test_determinism(self):
        f = {"risk_score": 0.45, "forecast_type": "node_failure", "deterministic_version": "v1", "input_hash": "abc"}
        a1 = SERVICE.build_assessment(f)
        a2 = SERVICE.build_assessment(f)
        assert a1 == a2

    def test_different_scores_produce_different_assessments(self):
        a_low = SERVICE.build_assessment({"risk_score": 0.1})
        a_high = SERVICE.build_assessment({"risk_score": 0.9})
        assert a_low["risk_level"] != a_high["risk_level"]
        assert a_low["recommendation"] != a_high["recommendation"]
        assert a_low["immutable_hash"] != a_high["immutable_hash"]

    def test_forecast_type_passed_through(self):
        a = SERVICE.build_assessment({"risk_score": 0.3, "forecast_type": "node_failure"})
        assert a["forecast_type"] == "node_failure"

    def test_input_hash_passed_through(self):
        a = SERVICE.build_assessment({"risk_score": 0.3, "input_hash": "abcd1234"})
        assert a["input_hash"] == "abcd1234"

    def test_empty_forecast_does_not_crash(self):
        a = SERVICE.build_assessment({})
        assert a["risk_level"] == "low"
        assert a["risk_score"] == 0.0
        assert a["advisory_only"] is True


# ── No auto-remediation ─────────────────────────────────────────────────────


class TestNoAutoRemediation:

    def test_recommendations_never_claim_auto_remediation(self):
        forbidden = ["self-heal", "automatic remediation", "automatically remediate", "auto-remediating"]
        for level in ("low", "medium", "high", "critical"):
            rec = SERVICE.recommendation_for_level(level)
            for word in forbidden:
                assert word not in rec.lower()

    def test_assessment_is_advisory_only_across_all_levels(self):
        for score in [0.0, 0.3, 0.6, 0.9]:
            a = SERVICE.build_assessment({"risk_score": score})
            assert a["advisory_only"] is True

    def test_critical_mentions_approval_not_enforcement(self):
        rec = SERVICE.recommendation_for_level("critical")
        assert "approval" in rec.lower()
        assert "enforcement" not in rec.lower()

    def test_high_mentions_approval_not_enforcement(self):
        rec = SERVICE.recommendation_for_level("high")
        assert "approval" in rec.lower()
        assert "enforcement" not in rec.lower()


# ── Edge cases ───────────────────────────────────────────────────────────────


class TestEdgeCases:

    def test_forecast_with_negative_risk_score(self):
        a = SERVICE.build_assessment({"risk_score": -0.5})
        assert a["risk_level"] == "low"
        assert a["risk_score"] == -0.5

    def test_forecast_with_none_risk_score(self):
        a = SERVICE.build_assessment({"risk_score": None})
        assert a["risk_level"] == "low"
        assert a["risk_score"] == 0.0

    def test_forecast_with_string_risk_score(self):
        a = SERVICE.build_assessment({"risk_score": "bad"})
        assert a["risk_level"] == "low"
        assert a["risk_score"] == 0.0
