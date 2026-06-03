import os

from scripts.llm_harness.models import ExecutionResult
from scripts.llm_harness.reporter import Reporter


def test_reporter_generation(tmp_path):
    output_dir = str(tmp_path / "reports")
    reporter = Reporter(output_dir=output_dir)
    result = ExecutionResult(
        success=True,
        message="Done",
        duration=1.5,
        trace_id="trace-123",
        trace_hash="abc123",
        events=[{"event": "run.completed"}],
    )
    filename = reporter.generate_summary(result, trace=[{"step": 1, "output": "ok"}])
    assert os.path.exists(os.path.join(output_dir, filename))
    with open(os.path.join(output_dir, filename), "r") as f:
        data = f.read()
        assert '"events"' in data
        assert '"trace_id": "trace-123"' in data
        assert '"trace_hash": "abc123"' in data


def test_reporter_stub_warning(tmp_path):
    output_dir = str(tmp_path / "stub_reports")
    reporter = Reporter(output_dir=output_dir)
    result = ExecutionResult(success=True, message="Done", duration=1.0)

    # Test JSON with stub
    filename = reporter.generate_summary(result, trace=[], policy_info={"provider": "stub"})
    with open(os.path.join(output_dir, filename), "r") as f:
        data = f.read()
        assert "stub" in data
        assert "warning" in data

    # Test Markdown with stub
    report_md = reporter.generate_markdown_report(result, provider="stub")
    assert "WARNING" in report_md
    assert "stub" in report_md


def test_reporter_includes_parsed_summary(tmp_path):
    output_dir = str(tmp_path / "parsed_reports")
    reporter = Reporter(output_dir=output_dir)
    result = ExecutionResult(
        success=False,
        error="tests failed",
        duration=1.0,
        events=[
            {
                "event": "action.failed",
                "action_type": "run_shell",
                "status": "failed",
                "step": 2,
                "duration_ms": 12,
                "message": "pytest reported 1 failure(s)",
                "metadata": {
                    "parsed": {
                        "kind": "pytest",
                        "summary": "pytest reported 1 failure(s)",
                        "failures": [{"location": "tests/test_demo.py::test_nope", "message": "AssertionError"}],
                        "error_count": 1,
                        "warning_count": 0,
                    }
                },
            }
        ],
    )

    report_md = reporter.generate_markdown_report(result)
    assert "Parsed Output" in report_md
    assert "pytest reported 1 failure(s)" in report_md


def test_reporter_includes_blocked_actions_and_trace_metadata(tmp_path):
    output_dir = str(tmp_path / "trace_reports")
    reporter = Reporter(output_dir=output_dir)
    result = ExecutionResult(
        success=False,
        error="blocked",
        duration=1.0,
        trace_id="trace-456",
        trace_hash="hash-456",
        events=[
            {
                "event": "policy.blocked",
                "action_type": "run_shell",
                "status": "blocked",
                "step": 2,
                "duration_ms": 0,
                "message": "rm -rf / blocked",
            }
        ],
    )

    filename = reporter.generate_summary(result, trace=[{"step": 2, "blocked": True}])
    data = (tmp_path / "trace_reports" / filename).read_text()
    assert '"blocked_actions"' in data

    report_md = reporter.generate_markdown_report(
        result,
        blocked_actions=["rm -rf / blocked"],
    )
    assert "Trace ID" in report_md
    assert "trace-456" in report_md
    assert "hash-456" in report_md
