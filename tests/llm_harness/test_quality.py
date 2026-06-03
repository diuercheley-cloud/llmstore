from scripts.llm_harness._logging import setup_logging
from scripts.llm_harness.models import ExecutionResult


def test_logging_setup():
    # Just ensures logging setup does not raise.
    setup_logging()


def test_models_validation():
    res = ExecutionResult(success=True, message="Ok")
    assert res.success is True
    assert res.duration == 0.0
