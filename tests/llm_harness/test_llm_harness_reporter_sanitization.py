from scripts.llm_harness.models import ExecutionResult
from scripts.llm_harness.reporter import Reporter


def test_reporter_markdown_sanitization():
    reporter = Reporter()
    result = ExecutionResult(
        success=True,
        message="Done <script>alert(1)</script> Authorization: Bearer token-123",
        events=[{"event": "run.completed", "message": "api_key=sk-secret"}],
    )
    report = reporter.generate_markdown_report(result)
    assert "SUCCESS" in report
    assert "Done" in report
    assert "token-123" not in report
