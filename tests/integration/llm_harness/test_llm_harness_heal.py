from scripts.llm_harness.heal import HealEngine, SQLAlchemyHealRule
from scripts.llm_harness.models import ExecutionResult, HarnessEvent


def test_sqlalchemy_rule():
    rule = SQLAlchemyHealRule()
    error = "sqlalchemy.exc.MissingGreenlet: ... async_orm_lazy_load"
    classification = rule.classify_error(error)
    assert classification == "sqlalchemy_lazy_load"

    suggestion = rule.suggest_fix(classification)
    assert "selectinload" in suggestion


def test_heal_engine_unknown():
    engine = HealEngine()
    result = engine.analyze_error("Some random error")
    assert result["classification"] == "unknown"
    assert "No automated fix" in result["suggestion"]


def test_execution_result_metrics():
    res = ExecutionResult(
        success=True,
        duration=1.5,
        total_duration_ms=1500.0,
        command_duration_ms=500.0,
        agent_latency_ms=1000.0,
        retry_count=1,
    )
    assert res.total_duration_ms == 1500.0
    assert res.agent_latency_ms == 1000.0


def test_harness_event_metrics():
    event = HarnessEvent(
        event="action.completed",
        action_type="run_shell",
        step=1,
        status="completed",
        duration_ms=100,
        agent_latency_ms=0,
    )
    assert event.duration_ms == 100
    assert event.agent_latency_ms == 0
