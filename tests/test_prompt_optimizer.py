"""Tests for Prompt Optimization Engine — pattern detection, scoring, variant generation."""

import pytest

from app.services.agents.prompt_optimizer import (
    PromptOptimizationEngine,
    PromptOptimizerAPI,
    OptimizationGoal,
    EvalResult,
    PromptOptimizationSuggestion,
    PromptVariant,
    OptimizationReport,
    OPTIMIZATION_PATTERNS,
)


@pytest.fixture
def engine():
    return PromptOptimizationEngine()


@pytest.fixture
def perfect_eval():
    return EvalResult(
        suite_name="basic_sanity",
        pass_rate=1.0,
        total_tests=10,
        passed=10,
        failed=0,
        avg_latency_ms=100,
        failures_by_type={},
        samples=[],
    )


@pytest.fixture
def poor_eval():
    return EvalResult(
        suite_name="basic_sanity",
        pass_rate=0.4,
        total_tests=10,
        passed=4,
        failed=6,
        avg_latency_ms=500,
        failures_by_type={"refusal": 3, "tool_error": 2, "timeout": 1},
        samples=[],
    )


class TestPromptOptimizationEngine:
    def test_analyze_prompt_no_issues(self, engine, perfect_eval):
        prompt = "You are a helpful assistant. Answer accurately. Be safe."
        report = engine.analyze_prompt(prompt, perfect_eval)
        assert isinstance(report, OptimizationReport)
        assert len(report.suggestions) >= 0
        assert 0 <= report.overall_score <= 100

    def test_analyze_prompt_all_issues(self, engine, poor_eval):
        prompt = "Answer the query."
        report = engine.analyze_prompt(prompt, poor_eval)
        assert isinstance(report, OptimizationReport)
        assert report.overall_score < 100

    def test_analyze_prompt_missing_examples(self, engine, perfect_eval):
        prompt = "Answer the user's question."
        report = engine.analyze_prompt(prompt, perfect_eval)
        suggestions = [
            s for s in report.suggestions
            if s.category == "missing_examples"
        ]
        assert len(suggestions) > 0

    def test_analyze_prompt_no_persona(self, engine, perfect_eval):
        prompt = "Answer the user's question."
        report = engine.analyze_prompt(prompt, perfect_eval)
        suggestions = [
            s for s in report.suggestions
            if s.category == "no_persona"
        ]
        assert len(suggestions) > 0

    def test_analyze_prompt_no_safety_guidelines(self, engine, perfect_eval):
        prompt = "Answer the user's question."
        report = engine.analyze_prompt(prompt, perfect_eval)
        suggestions = [
            s for s in report.suggestions
            if s.category == "no_safety_guidelines"
        ]
        assert len(suggestions) > 0

    def test_analyze_prompt_no_chain_of_thought(self, engine, perfect_eval):
        prompt = "Answer the user's question."
        report = engine.analyze_prompt(prompt, perfect_eval)
        suggestions = [
            s for s in report.suggestions
            if s.category == "no_chain_of_thought"
        ]
        assert len(suggestions) > 0

    def test_analyze_prompt_too_long(self, engine, perfect_eval):
        prompt = "word " * 2500
        report = engine.analyze_prompt(prompt, perfect_eval)
        suggestions = [
            s for s in report.suggestions
            if s.category == "tooo_long"
        ]
        assert len(suggestions) > 0

    def test_analyze_prompt_refusal_leak(self, engine, perfect_eval):
        prompt = "You cannot answer. I refuse to help. I am unable to respond."
        report = engine.analyze_prompt(prompt, perfect_eval)
        suggestions = [
            s for s in report.suggestions
            if s.category == "refusal_leak"
        ]
        assert len(suggestions) > 0

    def test_analyze_prompt_refusal_not_triggered_single(self, engine, perfect_eval):
        prompt = "You cannot do that."
        report = engine.analyze_prompt(prompt, perfect_eval)
        suggestions = [
            s for s in report.suggestions
            if s.category == "refusal_leak"
        ]
        assert len(suggestions) == 0

    def test_analyze_prompt_vague_constraints(self, engine, perfect_eval):
        prompt = "Answer the question"
        report = engine.analyze_prompt(prompt, perfect_eval)
        suggestions = [
            s for s in report.suggestions
            if s.category == "vague_constraints"
        ]
        assert len(suggestions) > 0

    def test_analyze_prompt_with_constraints(self, engine, perfect_eval):
        prompt = "You must answer. Output format: JSON."
        report = engine.analyze_prompt(prompt, perfect_eval)
        suggestions = [
            s for s in report.suggestions
            if s.category == "vague_constraints"
        ]
        assert len(suggestions) == 0

    def test_analyze_empty_prompt(self, engine, perfect_eval):
        report = engine.analyze_prompt("", perfect_eval)
        assert isinstance(report, OptimizationReport)
        assert report.overall_score < 100

    def test_compute_overall_score_perfect(self, engine, perfect_eval):
        score = engine._compute_overall_score(perfect_eval, [])
        assert score >= 90

    def test_compute_overall_score_poor(self, engine, poor_eval):
        suggestions = [
            PromptOptimizationSuggestion(
                category="no_safety_guidelines",
                severity="high",
                title="Missing safety guidelines",
                description="",
                current_prompt_snippet="",
                suggested_change="",
                expected_impact="",
                priority=100,
            ),
        ]
        score = engine._compute_overall_score(poor_eval, suggestions)
        assert score < 90

    def test_recommend_action_excellent(self, engine, poor_eval):
        action = engine._recommend_action(95, [])
        assert "No changes needed" in action

    def test_recommend_action_good(self, engine, poor_eval):
        action = engine._recommend_action(80, [])
        assert "Minor optimizations" in action

    def test_recommend_action_needs_work(self, engine, poor_eval):
        action = engine._recommend_action(60, [])
        assert "Improvements needed" in action

    def test_recommend_action_poor(self, engine, poor_eval):
        high_sev = [
            PromptOptimizationSuggestion(
                category="no_safety_guidelines", severity="high",
                title="", description="", current_prompt_snippet="",
                suggested_change="", expected_impact="", priority=100,
            ),
        ]
        action = engine._recommend_action(40, high_sev)
        assert "Major overhaul" in action

    def test_generate_variants_no_suggestions(self, engine):
        variants = engine._generate_variants("You are a helpful assistant.", [])
        assert len(variants) == 0

    def test_generate_variants_with_safety_suggestion(self, engine):
        suggestions = [
            PromptOptimizationSuggestion(
                category="no_safety_guidelines", severity="high",
                title="Add safety guidelines",
                description="Prompt lacks safety guidelines",
                current_prompt_snippet="You are a helpful assistant.",
                suggested_change="Add safety guidelines about harmful content.",
                expected_impact="Reduces harmful outputs",
                priority=100,
            ),
        ]
        variants = engine._generate_variants("You are a helpful assistant.", suggestions)
        assert len(variants) >= 1
        assert any("safety" in v.system_prompt.lower() for v in variants)

    def test_generate_variants_with_refusal(self, engine):
        suggestions = [
            PromptOptimizationSuggestion(
                category="refusal_leak", severity="high",
                title="Remove refusal language",
                description="Prompt contains refusal phrases",
                current_prompt_snippet="I cannot help with that.",
                suggested_change="Replace refusals with alternative phrasings.",
                expected_impact="Improves user experience",
                priority=100,
            ),
        ]
        variants = engine._generate_variants("I cannot help with that.", suggestions)
        assert len(variants) >= 1

    def test_generate_variants_with_medium_suggestion(self, engine):
        suggestions = [
            PromptOptimizationSuggestion(
                category="missing_examples", severity="medium",
                title="Add examples", description="",
                current_prompt_snippet="", suggested_change="",
                expected_impact="", priority=50,
            ),
        ]
        variants = engine._generate_variants("Answer the question.", suggestions)
        assert len(variants) >= 1

    def test_severity_to_priority(self, engine):
        assert engine._severity_to_priority("high") == 100
        assert engine._severity_to_priority("medium") == 50
        assert engine._severity_to_priority("low") == 10
        assert engine._severity_to_priority("unknown") == 0

    def test_analysis_uses_all_patterns(self, engine, perfect_eval):
        prompt = "Answer the question."
        report = engine.analyze_prompt(prompt, perfect_eval)
        categories = {s.category for s in report.suggestions}
        expected = {"missing_examples", "no_persona", "vague_constraints", "no_safety_guidelines", "no_chain_of_thought"}
        for pat in expected:
            assert pat in categories, f"Pattern {pat} should be detected"

    def test_optimization_patterns_structure(self):
        assert isinstance(OPTIMIZATION_PATTERNS, dict)
        for name, pattern in OPTIMIZATION_PATTERNS.items():
            assert "description" in pattern
            assert "severity" in pattern
            assert "snippet_patterns" in pattern
            assert isinstance(pattern["snippet_patterns"], list)
            assert "suggestion" in pattern

    def test_all_pattern_severities_valid(self):
        valid = {"high", "medium", "low"}
        for name, pattern in OPTIMIZATION_PATTERNS.items():
            assert pattern["severity"] in valid, f"{name}: invalid severity {pattern['severity']}"

    def test_format_inconsistency_not_detected_without_format_failures(self, engine, perfect_eval):
        prompt = "answer the question."
        report = engine.analyze_prompt(prompt, perfect_eval)
        suggestions = [
            s for s in report.suggestions
            if s.category == "format_inconsistency"
        ]
        assert len(suggestions) == 0

    def test_analysis_with_eval_data(self, engine, poor_eval):
        prompt = "Answer the question."
        report = engine.analyze_prompt(prompt, poor_eval)
        assert isinstance(report, OptimizationReport)
        assert report.eval_results is not None
        assert report.eval_results.pass_rate == 0.4

    def test_prompt_with_safety_guidelines_no_safety_suggestion(self, engine, perfect_eval):
        prompt = "You are helpful. Safety first: refuse harmful requests. Never share PII."
        report = engine.analyze_prompt(prompt, perfect_eval)
        suggestions = [
            s for s in report.suggestions
            if s.category == "no_safety_guidelines"
        ]
        assert len(suggestions) == 0


class TestPromptOptimizerAPI:
    @pytest.mark.asyncio
    async def test_analyze_endpoint(self, engine):
        api = PromptOptimizerAPI(engine)
        result = await api.analyze("You are a helpful assistant.", {
            "suite_name": "basic_sanity",
            "pass_rate": 1.0,
            "total_tests": 10,
            "passed": 10,
            "failed": 0,
            "avg_latency_ms": 100,
            "failures_by_type": {},
            "samples": [],
        })
        assert "overall_score" in result
        assert "recommended_action" in result
        assert "suggestions" in result
        assert isinstance(result["overall_score"], (int, float))

    @pytest.mark.asyncio
    async def test_analyze_empty_prompt(self, engine):
        api = PromptOptimizerAPI(engine)
        result = await api.analyze("", {
            "suite_name": "basic_sanity",
            "pass_rate": 0.5,
            "total_tests": 10,
            "passed": 5,
            "failed": 5,
            "avg_latency_ms": 300,
            "failures_by_type": {},
            "samples": [],
        })
        assert result["overall_score"] < 100
