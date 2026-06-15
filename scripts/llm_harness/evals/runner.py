import asyncio
import logging
import os
import subprocess
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .._logging import setup_logging
from ..config import HarnessConfig
from ..legacy_runner import run_harness
from ..sanitizer import Sanitizer
from .judge import create_judge
from .loader import EvalLoader
from .report import EvalReportGenerator
from .schema import CaseScore, EvalResult, EvalSuite, JudgeVerdictModel
from .scorers import Scorer, score_case
from .tracking import ExperimentConfig, LocalExperimentTracker, MLflowExporter, RunMetrics

logger = logging.getLogger(__name__)


class EvalRunner:
    def __init__(
        self,
        suite: EvalSuite,
        provider: str = "stub",
        model: str = "",
        base_url: str = "",
        api_key_env: str = "OPENAI_API_KEY",
        allow_stub: bool = True,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
        sandbox: bool = False,
        docker_image: str = "python:3.12-slim",
        self_heal: bool = True,
        max_steps: int = 10,
        request_timeout: float = 30.0,
        max_retries: int = 3,
        workspace_mount_path: str = "/workspace",
        temp_base_dir: str | None = None,
        max_output_chars: int = 10000,
        report_output_path: str = "artifacts/llm_harness",
        judge_provider: str = "disabled",
        judge_model: str = "",
        judge_base_url: str = "",
        judge_api_key_env: str = "OPENAI_API_KEY",
        judge_threshold: float = 0.75,
        track: bool = False,
        track_dir: str = "artifacts/evals/runs",
        prompt_version: str = "",
        prompt_hash: str = "",
        policy_preset: str = "",
        suite_path: str = "",
        pricing_file: str | None = None,
        max_cost_per_run: float | None = None,
        max_tokens_per_run: int | None = None,
        model_max_tokens: int | None = None,
        experiment_tracker: str = "local",
        mlflow_tracking_uri: str | None = None,
        mlflow_experiment: str | None = None,
    ):
        self.suite = suite
        self.provider = provider
        self.model = model
        self.base_url = base_url
        self.api_key_env = api_key_env
        self.allow_stub = allow_stub
        self.progress_callback = progress_callback
        self.sandbox = sandbox
        self.docker_image = docker_image
        self.self_heal = self_heal
        self.max_steps = max_steps
        self.request_timeout = request_timeout
        self.max_retries = max_retries
        self.workspace_mount_path = workspace_mount_path
        self.temp_base_dir = temp_base_dir
        self.max_output_chars = max_output_chars
        self.report_output_path = report_output_path

        self.judge_provider = judge_provider
        self.judge_threshold = judge_threshold
        self._judge_instance: Any = None
        self._judge_config: dict[str, Any] = {
            "provider": judge_provider,
            "model": judge_model,
            "base_url": judge_base_url,
            "api_key_env": judge_api_key_env,
            "threshold": judge_threshold,
        }

        self.track = track
        self.track_dir = track_dir
        self.prompt_version = prompt_version
        self.prompt_hash = prompt_hash
        self.policy_preset = policy_preset
        self.suite_path = suite_path
        self.pricing_file = pricing_file
        self.max_cost_per_run = max_cost_per_run
        self.max_tokens_per_run = max_tokens_per_run
        self.model_max_tokens = model_max_tokens
        self.experiment_tracker = experiment_tracker
        self.mlflow_tracking_uri = mlflow_tracking_uri
        self.mlflow_experiment = mlflow_experiment

        self._tracker: LocalExperimentTracker | None = None
        self._run_id: str | None = None

    def _get_judge(self) -> Any:
        if self._judge_instance is None:
            self._judge_instance = create_judge(str(self.judge_provider), self._judge_config)
        return self._judge_instance

    async def run_all(self, concurrency: int = 1) -> EvalResult:
        setup_logging()
        logger.info(
            "Starting eval suite '%s' with %d case(s), concurrency=%d",
            self.suite.name,
            len(self.suite.cases),
            concurrency,
        )

        if self.track:
            self._tracker = LocalExperimentTracker(base_dir=self.track_dir)
            exp_config = ExperimentConfig(
                model=str(self.model),
                provider=str(self.provider),
                prompt_version=str(self.prompt_version),
                prompt_hash=str(self.prompt_hash),
                policy_preset=str(self.policy_preset),
                sandbox=bool(self.sandbox),
                judge_provider=str(self.judge_provider),
                judge_model=str(self._judge_config.get("model", "")),
                judge_threshold=float(self.judge_threshold),
                max_steps=int(self.max_steps),
                suite_name=str(self.suite.name),
                suite_path=str(self.suite_path),
            )
            self._run_id = self._tracker.create_run(exp_config)
            logger.info("Experiment tracking enabled, run_id=%s", self._run_id)

        semaphore = asyncio.Semaphore(concurrency)
        total_tokens = 0
        estimated_cost = 0.0

        async def run_single(case_index: int):
            async with semaphore:
                score, tokens = await self._run_case(case_index)
                return score, tokens

        tasks = [run_single(i) for i in range(len(self.suite.cases))]
        results = await asyncio.gather(*tasks)

        case_scores: list[CaseScore] = []
        for score, tokens in results:
            case_scores.append(score)
            total_tokens += tokens

        result = Scorer.aggregate(self.suite, case_scores)
        result.total_tokens = total_tokens

        feedback = Scorer.generate_feedback(result)
        logger.info(feedback)

        # Store feedback in memory if available
        # Need to import LocalMemory and initialize it if enabled
        from ..memory import LocalMemory

        # Re-using track_dir for memory if not explicitly provided
        memory = LocalMemory(memory_dir=".llm_harness_memory")
        memory.store_eval_feedback(self.suite.name, feedback)

        judge_scores = [
            cs.judge_verdict.score for cs in case_scores if cs.judge_verdict is not None
        ]
        judge_avg = sum(judge_scores) / len(judge_scores) if judge_scores else 0.0

        if self.track and self._tracker and self._run_id:
            await self._save_tracking(result, judge_avg, total_tokens, estimated_cost)

        logger.info(
            "Eval suite '%s' complete: %d/%d passed (accuracy=%.2f%%, judge=%.2f)",
            self.suite.name,
            result.passed,
            result.total_cases,
            result.accuracy * 100,
            judge_avg,
        )
        return result

    async def _save_tracking(
        self,
        result: EvalResult,
        judge_avg_score: float,
        total_tokens: int,
        estimated_cost: float,
    ):
        tracker = self._tracker
        if tracker is None:
            return
        run_dir = tracker.run_dir

        summary = EvalReportGenerator.generate_summary(result)
        tracker.save_results(summary)

        md = EvalReportGenerator.generate_markdown_report(result)
        tracker.save_report(md)

        for cs in result.case_scores:
            case_data: dict[str, Any] = {
                "case_id": cs.case_id,
                "passed": cs.passed,
                "checks": cs.checks,
                "details": cs.details,
                "duration_seconds": cs.duration_seconds,
                "error": cs.error,
            }
            if cs.judge_verdict:
                case_data["judge_verdict"] = cs.judge_verdict.model_dump()
            tracker.save_case(cs.case_id, case_data)

        metrics = RunMetrics(
            accuracy=result.accuracy,
            pass_at_1=result.pass_at_1,
            judge_avg_score=judge_avg_score,
            total_duration_ms=result.total_duration_seconds * 1000,
            total_tokens=total_tokens,
            estimated_cost=estimated_cost,
        )
        tracker.save_metrics(metrics)

        if self.experiment_tracker == "mlflow":
            exporter = MLflowExporter()
            metadata = {
                "run_id": self._run_id,
                "config": metrics.to_dict(),
                "metrics": metrics.to_dict(),
            }
            if self.mlflow_tracking_uri:
                import os

                os.environ["MLFLOW_TRACKING_URI"] = self.mlflow_tracking_uri

            exporter.export_run(tracker.run_dir, metadata)

        logger.info("Experiment run saved to %s", run_dir)

    async def _run_case(self, case_index: int) -> tuple[CaseScore, int]:
        case = self.suite.cases[case_index]
        logger.info("Running case '%s': %s", case.id, case.task)

        from ..tracing import Tracer

        tracer = Tracer()
        span_id = tracer.start_span("eval_case", attributes={"case_id": case.id, "task": case.task})
        loop_timeout = case.timeout_seconds or 300
        start = time.time()
        tokens = 0

        try:
            with tempfile.TemporaryDirectory(prefix="agent-harness-") as workspace_dir:
                self._materialize_input_files(workspace_dir, case.input_files or {})
                harness_result = await run_harness(
                    task=case.task,
                    workspace_path=workspace_dir,
                    allow_stub=self.allow_stub,
                    progress_callback=self.progress_callback,
                    config=HarnessConfig(
                        code_agent="eval-agent",
                        provider=self.provider,
                        model=self.model,
                        base_url=self.base_url,
                        api_key_env=self.api_key_env,
                        sandbox=self.sandbox,
                        docker_image=self.docker_image,
                        test_command="pytest",
                        max_steps=self.max_steps,
                        self_heal=self.self_heal,
                        timeout=self.request_timeout,
                        max_retries=self.max_retries,
                        workspace_mount_path=self.workspace_mount_path,
                        temp_base_dir=self.temp_base_dir,
                        loop_timeout=loop_timeout,
                        max_output_chars=self.max_output_chars,
                        report_output_path=self.report_output_path,
                        pricing_file=self.pricing_file,
                        max_cost_per_run=self.max_cost_per_run,
                        max_tokens_per_run=self.max_tokens_per_run,
                        max_tokens=self.model_max_tokens,
                    ),
                    allow_test_short_circuit=(self.provider == "stub"),
                )

                test_command_result = None
                if case.test_command:
                    test_command_result = await self._execute_test_command(
                        workspace_dir, case.test_command
                    )

                elapsed = time.time() - start
                score = score_case(
                    case,
                    harness_result,
                    elapsed,
                    test_command_result=test_command_result,
                )

            # Judge evaluation
            if self.judge_provider != "disabled":
                try:
                    judge = self._get_judge()
                    diff = self._extract_diff(harness_result)
                    test_output = self._extract_test_output(harness_result)
                    harness_report = self._extract_harness_report(harness_result)

                    verdict = await judge.judge(
                        task=case.task,
                        diff=diff,
                        test_output=test_output,
                        harness_report=harness_report,
                    )

                    score.judge_verdict = JudgeVerdictModel(
                        score=verdict.score,
                        passed=verdict.passed,
                        reason=Sanitizer.sanitize_text(verdict.reason),
                        strengths=[Sanitizer.sanitize_text(s) for s in verdict.strengths],
                        weaknesses=[Sanitizer.sanitize_text(w) for w in verdict.weaknesses],
                        risk_level=verdict.risk_level,
                    )

                    if verdict.score < self.judge_threshold:
                        score.passed = False
                        score.checks["judge_score"] = False
                        existing = score.error or ""
                        suffix = (
                            f"Judge score {verdict.score:.2f}"
                            f" below threshold {self.judge_threshold}"
                        )
                        score.error = f"{existing}; {suffix}".strip("; ")
                    else:
                        score.checks["judge_score"] = True

                except Exception as exc:
                    logger.error("Judge failed for case '%s': %s", case.id, exc)

            logger.info(
                "Case '%s': %s (%.2fs)",
                case.id,
                "PASS" if score.passed else "FAIL",
                elapsed,
            )
            tracer.end_span(span_id, success=score.passed, error=score.error)
            return score, tokens

        except Exception as exc:
            elapsed = time.time() - start
            logger.error("Case '%s' failed with exception: %s", case.id, exc)
            tracer.end_span(span_id, success=False, error=str(exc))
            return (
                CaseScore(
                    case_id=case.id,
                    passed=False,
                    checks={"harness_success": False},
                    details={"error": str(exc)},
                    duration_seconds=elapsed,
                    error=Sanitizer.sanitize_text(str(exc)),
                ),
                tokens,
            )

    @staticmethod
    def _materialize_input_files(workspace_dir: str, input_files: dict[str, str]) -> None:
        for relative_path, content in input_files.items():
            target = Path(workspace_dir) / relative_path
            os.makedirs(target.parent, exist_ok=True)
            target.write_text(content)

    @staticmethod
    async def _execute_test_command(workspace_dir: str, command: str) -> dict:
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=workspace_dir,
            )
            stdout, stderr = await proc.communicate()
            return {
                "returncode": proc.returncode or 0,
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
            }
        except Exception as exc:
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": str(exc),
            }

    def _extract_diff(self, harness_result) -> str:
        events = getattr(harness_result, "events", []) or []
        for ev in events:
            if ev.get("action_type") == "apply_patch" and ev.get("event") == "action.completed":
                metadata = ev.get("metadata") or {}
                return metadata.get("diff", "")
        return ""

    def _extract_test_output(self, harness_result) -> str:
        return getattr(harness_result, "output", "") or ""

    def _extract_harness_report(self, harness_result) -> str:
        parts = []
        events = getattr(harness_result, "events", []) or []
        for ev in events:
            action = ev.get("action_type", "")
            status = ev.get("status", "")
            msg = ev.get("message", "")
            parts.append(f"[{action}] {status}: {msg}")
        return "\n".join(parts)

    @classmethod
    def from_suite_path(
        cls,
        suite_path: str,
        **kwargs: Any,
    ) -> "EvalRunner":
        suite = EvalLoader.load(suite_path)
        if "suite_path" not in kwargs:
            kwargs["suite_path"] = suite_path
        return cls(suite=suite, **kwargs)
