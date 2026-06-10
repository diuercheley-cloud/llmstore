import asyncio
import json
import os
import shutil
import tempfile

import pytest

from scripts.llm_harness.evals import EvalRunner
from scripts.llm_harness.evals.judge import (
    DisabledJudgeProvider,
    JudgeVerdict,
    create_judge,
)
from scripts.llm_harness.evals.loader import EvalLoader, EvalLoadError, EvalSchemaError
from scripts.llm_harness.evals.report import EvalReportGenerator
from scripts.llm_harness.evals.schema import EvalCase, EvalResult, EvalSuite, JudgeVerdictModel
from scripts.llm_harness.evals.scorers import Scorer, score_case
from scripts.llm_harness.evals.tracking import ExperimentConfig, LocalExperimentTracker, RunMetrics
from scripts.llm_harness.models import ExecutionResult

# ── Fixtures ──────────────────────────────────────────────────────────────────

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture
def sample_suite_path():
    return os.path.join(FIXTURE_DIR, "sample_eval_suite.json")


@pytest.fixture
def valid_suite_data():
    return {
        "name": "Test Suite",
        "description": "A test suite",
        "cases": [
            {
                "id": "case-1",
                "task": "Do something",
                "tags": ["basic"],
            },
            {
                "id": "case-2",
                "task": "Do something else",
                "test_command": "pytest",
                "timeout_seconds": 120,
                "tags": ["advanced"],
            },
        ],
    }


@pytest.fixture
def tmp_dir():
    path = tempfile.mkdtemp()
    yield path
    shutil.rmtree(path)


# ── Test: Loader ──────────────────────────────────────────────────────────────

class TestEvalLoader:

    def test_load_valid_suite(self, sample_suite_path):
        suite = EvalLoader.load(sample_suite_path)
        assert suite.name == "Sample Coding Eval Suite"
        assert len(suite.cases) == 1
        assert suite.cases[0].id == "fix-add-function"
        assert "add" in suite.cases[0].task

    def test_load_with_test_cases_fallback(self, tmp_dir):
        path = os.path.join(tmp_dir, "suite.json")
        data = {
            "name": "Legacy Suite",
            "test_cases": [
                {"name": "legacy-1", "input": "Do task", "input_text": "Do task"},
            ],
        }
        with open(path, "w") as f:
            json.dump(data, f)
        suite = EvalLoader.load(path)
        assert suite.name == "Legacy Suite"
        assert len(suite.cases) == 1
        assert suite.cases[0].task == "Do task"

    def test_reject_missing_file(self):
        with pytest.raises(EvalLoadError, match="not found"):
            EvalLoader.load("/nonexistent/path.json")

    def test_reject_invalid_json(self, tmp_dir):
        path = os.path.join(tmp_dir, "bad.json")
        with open(path, "w") as f:
            f.write("not json")
        with pytest.raises(EvalLoadError, match="Failed to parse"):
            EvalLoader.load(path)

    def test_reject_non_object(self, tmp_dir):
        path = os.path.join(tmp_dir, "bad.json")
        with open(path, "w") as f:
            json.dump([1, 2, 3], f)
        with pytest.raises(EvalSchemaError, match="eval_suite must be a mapping"):
            EvalLoader.load(path)

    def test_reject_missing_name(self, tmp_dir):
        path = os.path.join(tmp_dir, "bad.json")
        with open(path, "w") as f:
            json.dump({"cases": []}, f)
        with pytest.raises(EvalSchemaError, match="name"):
            EvalLoader.load(path)

    def test_reject_missing_cases(self, tmp_dir):
        path = os.path.join(tmp_dir, "bad.json")
        with open(path, "w") as f:
            json.dump({"name": "Test"}, f)
        with pytest.raises(EvalSchemaError, match="cases"):
            EvalLoader.load(path)

    def test_reject_non_list_cases(self, tmp_dir):
        path = os.path.join(tmp_dir, "bad.json")
        with open(path, "w") as f:
            json.dump({"name": "Test", "cases": "not-a-list"}, f)
        with pytest.raises(EvalSchemaError, match="valid list"):
            EvalLoader.load(path)

    def test_reject_missing_task(self, tmp_dir):
        path = os.path.join(tmp_dir, "bad.json")
        with open(path, "w") as f:
            json.dump({"name": "Test", "cases": [{"id": "no-task"}]}, f)
        with pytest.raises(EvalSchemaError, match="task"):
            EvalLoader.load(path)

    def test_reject_non_object_case(self, tmp_dir):
        path = os.path.join(tmp_dir, "bad.json")
        with open(path, "w") as f:
            json.dump({"name": "Test", "cases": ["string-not-object"]}, f)
        with pytest.raises(EvalSchemaError, match="valid dictionary"):
            EvalLoader.load(path)

    def test_load_with_all_fields(self, tmp_dir):
        path = os.path.join(tmp_dir, "full.json")
        data = {
            "name": "Full Suite",
            "description": "Has all fields",
            "cases": [
                {
                    "id": "full-case",
                    "task": "Full task",
                    "input_files": {"test.txt": "hello"},
                    "expected_files": {"out.txt": "world"},
                    "test_command": "make check",
                    "expected_stdout": "PASS",
                    "expected_status": 0,
                    "timeout_seconds": 300,
                    "tags": ["full", "test"],
                }
            ],
        }
        with open(path, "w") as f:
            json.dump(data, f)
        suite = EvalLoader.load(path)
        assert len(suite.cases) == 1
        c = suite.cases[0]
        assert c.input_files == {"test.txt": "hello"}
        assert c.expected_files == {"out.txt": "world"}
        assert c.test_command == "make check"
        assert c.expected_stdout == "PASS"
        assert c.expected_status == 0
        assert c.timeout_seconds == 300
        assert c.tags == ["full", "test"]


# ── Test: Scorers ─────────────────────────────────────────────────────────────

class TestScorers:

    def test_score_case_pass(self):
        case = EvalCase(id="test-1", task="Do it")
        result = ExecutionResult(success=True, message="Done", output="All good")
        score = score_case(case, result, 1.5)
        assert score.passed is True
        assert score.checks["harness_success"] is True
        assert score.duration_seconds == 1.5

    def test_score_case_fail(self):
        case = EvalCase(id="test-2", task="Do it")
        result = ExecutionResult(success=False, error="Something broke")
        score = score_case(case, result, 2.0)
        assert score.passed is False
        assert score.checks["harness_success"] is False
        assert "Something broke" in score.details["harness_error"]

    def test_score_case_with_expected_stdout_contains(self):
        case = EvalCase(id="stdout-check", task="Run", expected_stdout="PASS")
        result = ExecutionResult(success=True, message="Done", output="All tests PASS")
        score = score_case(case, result, 1.0)
        assert score.passed is True
        assert score.checks["expected_stdout"] is True

    def test_score_case_with_expected_stdout_fails(self):
        case = EvalCase(id="stdout-fail", task="Run", expected_stdout="ERROR")
        result = ExecutionResult(success=True, message="Done", output="All good")
        score = score_case(case, result, 1.0)
        assert score.passed is False
        assert score.checks["expected_stdout"] is False

    def test_score_case_with_expected_status(self):
        case = EvalCase(id="status-check", task="Run", expected_status=0)
        result = ExecutionResult(success=True, message="Done")
        score = score_case(case, result, 1.0)
        assert score.passed is True

    def test_score_case_with_expected_files(self):
        case = EvalCase(
            id="file-check",
            task="Edit file",
            expected_files={"output.txt": "new content"},
        )
        result = ExecutionResult(
            success=True,
            message="Done",
            events=[
                {
                    "event": "action.completed",
                    "action_type": "apply_patch",
                    "metadata": {"changed_files": ["output.txt"]},
                }
            ],
        )
        score = score_case(case, result, 1.0)
        assert score.passed is True
        assert score.checks["file_match:output.txt"] is True

    def test_aggregate_all_pass(self):
        suite = EvalSuite(name="Test", cases=[EvalCase(id="a", task="a"), EvalCase(id="b", task="b")])
        scores = [
            score_case(suite.cases[0], ExecutionResult(success=True), 1.0),
            score_case(suite.cases[1], ExecutionResult(success=True), 2.0),
        ]
        result = Scorer.aggregate(suite, scores)
        assert result.total_cases == 2
        assert result.passed == 2
        assert result.failed == 0
        assert result.accuracy == 1.0
        assert result.pass_at_1 == 1.0
        assert result.total_duration_seconds == 3.0

    def test_aggregate_some_fail(self):
        suite = EvalSuite(name="Test", cases=[EvalCase(id="a", task="a"), EvalCase(id="b", task="b")])
        scores = [
            score_case(suite.cases[0], ExecutionResult(success=True), 1.0),
            score_case(suite.cases[1], ExecutionResult(success=False, error="fail"), 2.0),
        ]
        result = Scorer.aggregate(suite, scores)
        assert result.total_cases == 2
        assert result.passed == 1
        assert result.failed == 1
        assert result.accuracy == 0.5
        assert result.pass_at_1 == 0.5


# ── Test: Report ──────────────────────────────────────────────────────────────

class TestEvalReport:

    def test_generate_summary(self):
        suite = EvalSuite(name="Test", cases=[EvalCase(id="a", task="a")])
        scores = [score_case(suite.cases[0], ExecutionResult(success=True), 1.0)]
        result = Scorer.aggregate(suite, scores)
        summary = EvalReportGenerator.generate_summary(result)
        assert summary["suite_name"] == "Test"
        assert summary["total_cases"] == 1
        assert summary["passed"] == 1
        assert summary["failed"] == 0
        assert summary["accuracy"] == 1.0
        assert summary["pass_at_1"] == 1.0
        assert len(summary["case_results"]) == 1

    def test_save_json_report(self, tmp_dir):
        suite = EvalSuite(name="Test", cases=[EvalCase(id="a", task="a")])
        scores = [score_case(suite.cases[0], ExecutionResult(success=True), 1.0)]
        result = Scorer.aggregate(suite, scores)
        path = EvalReportGenerator.save_json_report(result, tmp_dir)
        assert os.path.exists(path)
        with open(path) as f:
            data = json.load(f)
        assert data["suite_name"] == "Test"
        assert data["passed"] == 1

    def test_generate_markdown_report(self):
        suite = EvalSuite(name="Test", cases=[EvalCase(id="a", task="a")])
        scores = [score_case(suite.cases[0], ExecutionResult(success=True), 1.0)]
        result = Scorer.aggregate(suite, scores)
        md = EvalReportGenerator.generate_markdown_report(result)
        assert "Eval Report: Test" in md
        assert "✅ PASS" in md
        assert "1/1" in md

    def test_generate_markdown_with_failures(self):
        error_text = "Something went wrong"
        suite = EvalSuite(name="Fail Suite", cases=[EvalCase(id="a", task="a")])
        scores = [
            score_case(
                suite.cases[0],
                ExecutionResult(success=False, error=error_text),
                2.0,
            )
        ]
        result = Scorer.aggregate(suite, scores)
        md = EvalReportGenerator.generate_markdown_report(result)
        assert "❌ FAIL" in md
        assert "Failed Cases Detail" in md
        assert "harness_success" in md

    def test_save_markdown_report(self, tmp_dir):
        suite = EvalSuite(name="Test", cases=[EvalCase(id="a", task="a")])
        scores = [score_case(suite.cases[0], ExecutionResult(success=True), 1.0)]
        result = Scorer.aggregate(suite, scores)
        path = EvalReportGenerator.save_markdown_report(result, tmp_dir)
        assert os.path.exists(path)

    def test_report_no_secrets(self, tmp_dir):
        suite = EvalSuite(name="Secure", cases=[EvalCase(id="s", task="secret task")])
        scores = [
            score_case(
                suite.cases[0],
                ExecutionResult(success=False, error="token=test-token-12345"),
                1.0,
            )
        ]
        result = Scorer.aggregate(suite, scores)
        json_path = EvalReportGenerator.save_json_report(result, tmp_dir)
        with open(json_path) as f:
            content = f.read()
        assert "test-token-12345" not in content

        md = EvalReportGenerator.generate_markdown_report(result)
        assert "test-token-12345" not in md


# ── Test: Runner (with stub) ──────────────────────────────────────────────────

class TestEvalRunner:

    @pytest.mark.asyncio
    async def test_run_with_stub_provider(self, sample_suite_path):
        suite = EvalLoader.load(sample_suite_path)
        runner = EvalRunner(
            suite=suite,
            provider="stub",
            allow_stub=True,
            max_steps=2,
        )
        result = await runner.run_all(concurrency=1)
        assert isinstance(result, EvalResult)
        assert result.suite_name == "Sample Coding Eval Suite"
        assert result.total_cases == 1

    @pytest.mark.asyncio
    async def test_run_all_pass_with_stub(self):
        suite = EvalSuite(
            name="Stub Pass",
            cases=[
                EvalCase(id="pass-1", task="Task 1"),
                EvalCase(id="pass-2", task="Task 2"),
            ],
        )
        runner = EvalRunner(suite=suite, provider="stub", allow_stub=True, max_steps=2)
        result = await runner.run_all(concurrency=2)
        assert result.total_cases == 2
        assert result.passed == 2
        assert result.accuracy == 1.0

    @pytest.mark.asyncio
    async def test_suite_from_path(self, sample_suite_path):
        runner = EvalRunner.from_suite_path(
            sample_suite_path,
            provider="stub",
            allow_stub=True,
            max_steps=2,
        )
        assert runner.suite.name == "Sample Coding Eval Suite"
        assert len(runner.suite.cases) == 1


# ── Test: CLI eval help ──────────────────────────────────────────────────────

class TestEvalCLI:

    def test_eval_help(self):
        import subprocess
        import sys
        result = subprocess.run(
            [sys.executable, "-m", "scripts.llm_harness.cli", "eval", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "--suite" in result.stdout
        assert "--code-agent" in result.stdout or "--provider" in result.stdout
        assert "--report" in result.stdout

    def test_eval_missing_suite(self):
        import subprocess
        import sys
        result = subprocess.run(
            [sys.executable, "-m", "scripts.llm_harness.cli", "eval", "--suite", "/nonexistent"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "not found" in result.stderr or "not found" in result.stdout

    def test_eval_help_includes_judge_flags(self):
        import subprocess
        import sys
        result = subprocess.run(
            [sys.executable, "-m", "scripts.llm_harness.cli", "eval", "--help"],
            capture_output=True,
            text=True,
        )
        assert "--judge" in result.stdout
        assert "--judge-model" in result.stdout
        assert "--judge-threshold" in result.stdout
        assert "--track" in result.stdout
        assert "--track-dir" in result.stdout


# ── Test: Judge ───────────────────────────────────────────────────────────────

class TestJudge:

    def test_judge_verdict_defaults(self):
        v = JudgeVerdict()
        assert v.score == 0.0
        assert v.passed is False
        assert v.reason == ""

    def test_judge_verdict_from_dict(self):
        data = {
            "score": 0.85,
            "passed": True,
            "reason": "Good solution",
            "strengths": ["Clean code"],
            "weaknesses": ["Missing error handling"],
            "risk_level": "low",
        }
        v = JudgeVerdict.from_dict(data)
        assert v.score == 0.85
        assert v.passed is True
        assert "Clean code" in v.strengths
        assert v.risk_level == "low"

    def test_judge_verdict_to_dict(self):
        v = JudgeVerdict(score=0.9, passed=True, reason="Ok", risk_level="low")
        d = v.to_dict()
        assert d["score"] == 0.9
        assert d["passed"] is True
        assert d["risk_level"] == "low"

    def test_disabled_judge_always_passes(self):
        judge = DisabledJudgeProvider({})
        verdict = asyncio.run(judge.judge(task="anything"))
        assert verdict.passed is True
        assert "disabled" in verdict.reason.lower()

    def test_create_judge_disabled(self):
        judge = create_judge("disabled", {})
        assert isinstance(judge, DisabledJudgeProvider)

    def test_create_judge_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown judge provider"):
            create_judge("nonexistent", {})

    def test_judge_verdict_model_pydantic(self):
        m = JudgeVerdictModel(score=0.95, passed=True, reason="Great", risk_level="low")
        assert m.score == 0.95
        assert m.passed is True

    @pytest.mark.asyncio
    async def test_judge_mock_returns_score(self):
        class MockJudge:
            async def judge(self, **kwargs):
                return JudgeVerdict(score=0.92, passed=True, reason="Mock OK")

        judge = MockJudge()
        verdict = await judge.judge(task="test")
        assert verdict.score == 0.92
        assert verdict.passed is True

    @pytest.mark.asyncio
    async def test_judge_score_below_threshold_marks_failed(self):
        suite = EvalSuite(name="Judge Test", cases=[EvalCase(id="j1", task="Test task")])

        mock_verdict = JudgeVerdict(score=0.3, passed=False, reason="Bad solution")

        class FailingJudge:
            async def judge(self, **kwargs):
                return mock_verdict

        runner = EvalRunner(
            suite=suite,
            provider="stub",
            allow_stub=True,
            max_steps=2,
            judge_provider="openai-compatible",
            judge_model="mock-model",
            judge_base_url="http://mock",
            judge_api_key_env="MOCK_KEY",
            judge_threshold=0.75,
        )
        runner._get_judge = lambda: FailingJudge()

        result = await runner.run_all(concurrency=1)
        assert result.passed == 0
        assert result.failed == 1
        cs = result.case_scores[0]
        assert cs.judge_verdict is not None
        assert cs.judge_verdict.score == 0.3
        assert cs.checks.get("judge_score") is False
        assert "below threshold" in (cs.error or "")

    @pytest.mark.asyncio
    async def test_judge_above_threshold_passes(self):
        suite = EvalSuite(name="Judge Pass", cases=[EvalCase(id="j2", task="Test")])

        class PassingJudge:
            async def judge(self, **kwargs):
                return JudgeVerdict(score=0.95, passed=True, reason="Great")

        runner = EvalRunner(
            suite=suite,
            provider="stub",
            allow_stub=True,
            max_steps=2,
            judge_provider="openai-compatible",
            judge_model="mock",
            judge_base_url="http://mock",
            judge_api_key_env="MOCK_KEY",
            judge_threshold=0.75,
        )
        runner._get_judge = lambda: PassingJudge()

        result = await runner.run_all(concurrency=1)
        assert result.passed == 1
        cs = result.case_scores[0]
        assert cs.checks.get("judge_score") is True

    def test_judge_config_from_args(self):
        from argparse import Namespace
        args = Namespace(
            judge="openai-compatible",
            judge_model="gpt-4",
            judge_base_url="http://localhost",
            judge_api_key_env="MY_KEY",
            judge_threshold=0.8,
        )
        config = {
            "provider": args.judge,
            "model": args.judge_model,
            "base_url": args.judge_base_url,
            "api_key_env": args.judge_api_key_env,
            "threshold": args.judge_threshold,
        }
        assert config["provider"] == "openai-compatible"
        assert config["threshold"] == 0.8

    @pytest.mark.asyncio
    async def test_judge_disabled_does_not_call_llm(self):
        suite = EvalSuite(name="No Judge", cases=[EvalCase(id="n1", task="Task")])
        runner = EvalRunner(
            suite=suite,
            provider="stub",
            allow_stub=True,
            max_steps=2,
            judge_provider="disabled",
        )
        result = await runner.run_all(concurrency=1)
        cs = result.case_scores[0]
        assert cs.judge_verdict is None


# ── Test: Tracking ────────────────────────────────────────────────────────────

class TestTracking:

    def test_experiment_config_to_dict(self):
        config = ExperimentConfig(
            model="gpt-4",
            provider="openai-compatible",
            prompt_version="v1",
            suite_name="Test Suite",
        )
        d = config.to_dict()
        assert d["model"] == "gpt-4"
        assert d["provider"] == "openai-compatible"
        assert d["prompt_version"] == "v1"
        assert d["suite_name"] == "Test Suite"

    def test_run_metrics_to_dict(self):
        metrics = RunMetrics(
            accuracy=0.85,
            pass_at_1=0.85,
            judge_avg_score=0.9,
            total_duration_ms=12345.67,
            total_tokens=500,
            estimated_cost=0.02,
        )
        d = metrics.to_dict()
        assert d["accuracy"] == 0.85
        assert d["pass_at_1"] == 0.85
        assert d["total_tokens"] == 500

    def test_tracker_creates_run(self, tmp_dir):
        tracker = LocalExperimentTracker(base_dir=tmp_dir)
        config = ExperimentConfig(model="gpt-4", provider="openai")
        run_id = tracker.create_run(config)
        assert run_id is not None
        assert os.path.isdir(tracker.run_dir)
        assert os.path.isdir(os.path.join(tracker.run_dir, "cases"))
        config_path = os.path.join(tracker.run_dir, "config.json")
        assert os.path.exists(config_path)
        with open(config_path) as f:
            data = json.load(f)
        assert data["model"] == "gpt-4"

    def test_tracker_save_results(self, tmp_dir):
        tracker = LocalExperimentTracker(base_dir=tmp_dir)
        tracker.create_run(ExperimentConfig())
        path = tracker.save_results({"passed": 5, "total": 10})
        assert os.path.exists(path)
        with open(path) as f:
            data = json.load(f)
        assert data["passed"] == 5

    def test_tracker_save_report(self, tmp_dir):
        tracker = LocalExperimentTracker(base_dir=tmp_dir)
        tracker.create_run(ExperimentConfig())
        path = tracker.save_report("# Eval Report\nPass: 5/10")
        assert os.path.exists(path)
        with open(path) as f:
            content = f.read()
        assert "Eval Report" in content

    def test_tracker_save_case(self, tmp_dir):
        tracker = LocalExperimentTracker(base_dir=tmp_dir)
        tracker.create_run(ExperimentConfig())
        path = tracker.save_case("case-1", {"passed": True, "score": 0.9})
        assert os.path.exists(path)
        assert "case-1" in path

    def test_tracker_save_metrics(self, tmp_dir):
        tracker = LocalExperimentTracker(base_dir=tmp_dir)
        tracker.create_run(ExperimentConfig())
        metrics = RunMetrics(accuracy=0.8, pass_at_1=0.8)
        path = tracker.save_metrics(metrics)
        assert os.path.exists(path)
        with open(path) as f:
            data = json.load(f)
        assert data["accuracy"] == 0.8

    def test_tracker_list_runs(self, tmp_dir):
        tracker = LocalExperimentTracker(base_dir=tmp_dir)
        tracker.create_run(ExperimentConfig(model="a"))
        tracker.create_run(ExperimentConfig(model="b"))
        runs = tracker.list_runs()
        assert len(runs) >= 2

    def test_tracker_compare_runs(self, tmp_dir):
        tracker = LocalExperimentTracker(base_dir=tmp_dir)
        tracker.create_run(ExperimentConfig(model="a"))
        id_a = tracker.run_id
        tracker.create_run(ExperimentConfig(model="b"))
        id_b = tracker.run_id

        comparison = tracker.compare_runs(id_a, id_b)
        assert "run_a" in comparison
        assert "run_b" in comparison
        assert "comparison" in comparison

    def test_tracker_no_secrets_in_files(self, tmp_dir):
        tracker = LocalExperimentTracker(base_dir=tmp_dir)
        tracker.create_run(ExperimentConfig(model="secret-model"))
        tracker.save_results({"token": "Bearer test-token-12345"})
        tracker.save_report("Report with api_key=test-api-key-12345")
        tracker.save_metrics(RunMetrics(accuracy=1.0))

        for root, _dirs, files in os.walk(tracker.run_dir):
            for fname in files:
                fpath = os.path.join(root, fname)
                with open(fpath) as f:
                    content = f.read()
                assert "test-token-12345" not in content
                assert "test-api-key-12345" not in content

    def test_tracker_no_secrets_in_config(self, tmp_dir):
        tracker = LocalExperimentTracker(base_dir=tmp_dir)
        config = ExperimentConfig(
            model="gpt-4",
            extra={"api_key": "Bearer test-token-12345"},
        )
        tracker.create_run(config)
        config_path = os.path.join(tracker.run_dir, "config.json")
        with open(config_path) as f:
            content = f.read()
        assert "test-token-12345" not in content
        assert "Bearer [REDACTED]" in content or "[REDACTED]" in content

    @pytest.mark.asyncio
    async def test_tracking_in_runner_saves_run(self, sample_suite_path, tmp_dir):
        suite = EvalLoader.load(sample_suite_path)
        tracker_dir = os.path.join(tmp_dir, "runs")
        runner = EvalRunner(
            suite=suite,
            provider="stub",
            allow_stub=True,
            max_steps=2,
            track=True,
            track_dir=tracker_dir,
        )
        await runner.run_all(concurrency=1)
        assert runner._run_id is not None
        run_dir = os.path.join(tracker_dir, runner._run_id)
        assert os.path.isdir(run_dir)
        assert os.path.exists(os.path.join(run_dir, "config.json"))
        assert os.path.exists(os.path.join(run_dir, "results.json"))
        assert os.path.exists(os.path.join(run_dir, "report.md"))
        assert os.path.exists(os.path.join(run_dir, "metrics.json"))

    @pytest.mark.asyncio
    async def test_report_contains_judge_info_in_markdown(self):
        suite = EvalSuite(name="Judge MD", cases=[EvalCase(id="jm1", task="Task")])
        harness_result = ExecutionResult(success=True, message="Done")
        score = score_case(suite.cases[0], harness_result, 1.0)
        score.judge_verdict = JudgeVerdictModel(
            score=0.88, passed=True, reason="Good", risk_level="low"
        )
        result = Scorer.aggregate(suite, [score])
        md = EvalReportGenerator.generate_markdown_report(result)
        assert "Judge Avg Score" in md
        assert "0.88" in md
        assert "Judge" in md.split("\n")[0]  # table header

    @pytest.mark.asyncio
    async def test_tracker_run_with_judge(self, tmp_dir):
        suite = EvalSuite(name="Track+Judge", cases=[EvalCase(id="tj1", task="Task")])

        class MockJudge:
            async def judge(self, **kwargs):
                return JudgeVerdict(score=0.95, passed=True, reason="OK")

        tracker_dir = os.path.join(tmp_dir, "runs")
        runner = EvalRunner(
            suite=suite,
            provider="stub",
            allow_stub=True,
            max_steps=2,
            track=True,
            track_dir=tracker_dir,
            judge_provider="openai-compatible",
            judge_model="mock",
            judge_base_url="http://mock",
            judge_api_key_env="MOCK_KEY",
            judge_threshold=0.75,
        )
        runner._get_judge = lambda: MockJudge()

        result = await runner.run_all(concurrency=1)
        assert result.passed == 1
        assert runner._run_id is not None

        results_path = os.path.join(tracker_dir, runner._run_id, "results.json")
        with open(results_path) as f:
            data = json.load(f)
        assert data["passed"] == 1

        cases_dir = os.path.join(tracker_dir, runner._run_id, "cases")
        case_files = os.listdir(cases_dir)
        assert len(case_files) == 1
        with open(os.path.join(cases_dir, case_files[0])) as f:
            case_data = json.load(f)
        assert "judge_verdict" in case_data
