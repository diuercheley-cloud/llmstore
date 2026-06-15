import uuid

import pytest
from app.services.agents.agent_evaluation_framework import (
    BENCHMARK_TASKS,
    AgentEvaluationService,
)


@pytest.mark.asyncio
async def test_agent_evaluation_framework_generates_metrics(tmp_path, session):
    service = AgentEvaluationService(session, artifacts_dir=tmp_path)
    report = await service.run_benchmark(uuid.uuid4(), "demo-model", "AgentBench")

    assert report.benchmark == "AgentBench"
    assert 0 <= report.metrics["success_rate"] <= 1
    assert 0 <= report.metrics["tool_efficiency"] <= 1
    assert report.metrics["latency_ms"] > 0
    assert report.metrics["token_cost"] >= 0
    assert 0 <= report.metrics["hallucination_score"] <= 1

    assert (tmp_path / "AgentBench" / report.run_id / "report.json").exists()
    assert (tmp_path / "AgentBench" / report.run_id / "report.csv").exists()
    assert (tmp_path / "AgentBench" / report.run_id / "report.md").exists()
    assert (tmp_path / "AgentBench" / report.run_id / "report.html").exists()


@pytest.mark.asyncio
async def test_agent_evaluation_framework_rejects_unknown_benchmark(tmp_path, session):
    service = AgentEvaluationService(session, artifacts_dir=tmp_path)
    with pytest.raises(ValueError, match="Unknown benchmark"):
        await service.run_benchmark(uuid.uuid4(), "demo-model", "InvalidBench")


@pytest.mark.asyncio
async def test_all_benchmarks_produce_valid_reports(tmp_path, session):
    service = AgentEvaluationService(session, artifacts_dir=tmp_path)
    for benchmark in BENCHMARK_TASKS:
        report = await service.run_benchmark(uuid.uuid4(), "test-model", benchmark)
        assert report.benchmark == benchmark
        assert len(report.results) == len(BENCHMARK_TASKS[benchmark])
        assert 0 <= report.metrics["success_rate"] <= 1
        assert report.metrics["latency_ms"] > 0


@pytest.mark.asyncio
async def test_list_benchmarks_returns_all(tmp_path, session):
    service = AgentEvaluationService(session, artifacts_dir=tmp_path)
    benchmarks = service.list_benchmarks()
    names = [b["name"] for b in benchmarks]
    assert "AgentBench" in names
    assert "GAIA" in names
    assert "BFCL" in names
    for b in benchmarks:
        assert b["tasks"] > 0
        assert b["supports"]["tool_calling"] is True


@pytest.mark.asyncio
async def test_export_csv(tmp_path, session):
    service = AgentEvaluationService(session, artifacts_dir=tmp_path)
    report = await service.run_benchmark(uuid.uuid4(), "demo-model", "BFCL")
    csv_data = service.export_csv(report)
    assert "task_id" in csv_data
    assert "bfcl-simple" in csv_data or "bfcl" in csv_data
    lines = csv_data.strip().split("\n")
    assert len(lines) > 1  # header + at least one row


@pytest.mark.asyncio
async def test_export_markdown(tmp_path, session):
    service = AgentEvaluationService(session, artifacts_dir=tmp_path)
    report = await service.run_benchmark(uuid.uuid4(), "demo-model", "GAIA")
    md = service.export_markdown(report)
    assert "# Agent Evaluation Report" in md
    assert "Success rate" in md
    assert report.run_id in md


@pytest.mark.asyncio
async def test_export_html(tmp_path, session):
    service = AgentEvaluationService(session, artifacts_dir=tmp_path)
    report = await service.run_benchmark(uuid.uuid4(), "demo-model", "AgentBench")
    html = service.export_html(report)
    assert "<html" in html
    assert "Success rate" in html
    assert report.run_id in html


@pytest.mark.asyncio
async def test_run_with_custom_runner(tmp_path, session):
    service = AgentEvaluationService(session, artifacts_dir=tmp_path)

    async def custom_runner(task):
        return {
            "output": f"custom result for {task.id}",
            "tool_calls": 2,
            "tokens_in": 100,
            "tokens_out": 50,
            "latency_ms": 300.0,
            "success": True,
            "sources": ["custom"],
        }

    report = await service.run_benchmark(
        uuid.uuid4(), "custom-model", "AgentBench", runner=custom_runner
    )
    assert report.metrics["success_rate"] == 1.0
    assert report.metrics["tool_efficiency"] > 0


@pytest.mark.asyncio
async def test_metrics_edge_cases(tmp_path, session):
    service = AgentEvaluationService(session, artifacts_dir=tmp_path)

    async def failing_runner(task):
        return {
            "output": "failed",
            "tool_calls": 0,
            "tokens_in": 10,
            "tokens_out": 5,
            "latency_ms": 50.0,
            "success": False,
            "error": "simulated failure",
        }

    report = await service.run_benchmark(uuid.uuid4(), "fail-model", "BFCL", runner=failing_runner)
    assert report.metrics["success_rate"] == 0.0
    assert report.metrics["tool_efficiency"] == 0.0
    assert report.metrics["hallucination_score"] >= 0
