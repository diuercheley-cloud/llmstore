import os

from scripts.llm_harness.models import ExecutionResult
from scripts.llm_harness.reporter import Reporter


def test_template_exists():
    template_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "scripts", "llm_harness", "templates", "report.md.jinja"
    )
    assert os.path.exists(template_path)

def test_markdown_report_rendering(tmp_path):
    reporter = Reporter(output_dir=str(tmp_path))
    result = ExecutionResult(
        success=True,
        message="All good",
        trace_id="trace-1",
        trace_hash="hash-1",
        duration=10.5,
        total_duration_ms=10500,
        command_duration_ms=2000,
        agent_latency_ms=8000,
        retry_count=2,
        events=[
            {
                "event": "action.completed",
                "step": 1,
                "action_type": "run_shell",
                "status": "completed",
                "duration_ms": 500,
                "message": "Command success"
            }
        ]
    )
    
    report = reporter.generate_markdown_report(result, blocked_actions=["rm -rf /"])
    
    assert "# Agent Execution Report" in report
    assert "- **Status**: SUCCESS" in report
    assert "- **Trace ID**: trace-1" in report
    assert "- **Trace Hash**: hash-1" in report
    assert "- **Total Duration**: 10.50s" in report
    assert "run_shell" in report
    assert "- rm -rf /" in report
    assert "- **Retry Count**: 2" in report

def test_json_summary_unchanged(tmp_path):
    reporter = Reporter(output_dir=str(tmp_path))
    result = ExecutionResult(
        success=True,
        message="Success message",
        duration=5.0
    )
    
    filename = reporter.generate_summary(result, trace=[{"step": 1}])
    assert filename.endswith(".json")
    
    with open(os.path.join(str(tmp_path), filename), "r") as f:
        import json
        data = json.load(f)
        assert data["success"] is True
        assert data["message"] == "Success message"
        assert data["duration"] == 5.0

def test_secrets_redaction_in_report(tmp_path):
    reporter = Reporter(output_dir=str(tmp_path))
    result = ExecutionResult(
        success=False,
        message="Failed with api_key=secret123",
        error="Unauthorized: Bearer sk-123456",
        duration=1.0,
        events=[
            {
                "event": "action.failed",
                "step": 1,
                "action_type": "run_shell",
                "status": "failed",
                "duration_ms": 100,
                "message": "Error with password=mypass"
            }
        ]
    )
    
    report = reporter.generate_markdown_report(result)
    
    assert "secret123" not in report
    assert "sk-123456" not in report
    assert "mypass" not in report
    assert "[REDACTED]" in report
