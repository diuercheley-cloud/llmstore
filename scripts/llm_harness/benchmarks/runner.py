# scripts/llm_harness/evals/runner.py
import json
import os
import time
from typing import Any

from ..config import HarnessConfig
from ..legacy_runner import run_harness


class BenchmarkSuiteRunner:
    def __init__(
        self,
        suite_path: str,
        provider: str = "stub",
        model: str = "",
        allow_stub: bool = True,
    ):
        self.suite_path = suite_path
        self.provider = provider
        self.model = model
        self.allow_stub = allow_stub
        self.results: list[dict[str, Any]] = []

    def load_suite(self) -> list[dict[str, Any]]:
        if not os.path.exists(self.suite_path):
            raise FileNotFoundError(f"Benchmark suite file not found: {self.suite_path}")
        with open(self.suite_path) as f:
            return json.load(f)

    async def run(self) -> dict[str, Any]:
        tasks = self.load_suite()
        self.results.clear()

        solved = 0
        failed = 0
        total_duration_ms = 0.0
        total_tokens = 0
        total_cost = 0.0

        for task in tasks:
            task_id = task.get("task_id") or task.get("instance_id") or "unknown"
            print(f"Running benchmark task: {task_id}")

            prompt = task.get("prompt") or task.get("problem_description") or ""
            test_code = task.get("test") or ""
            entry_point = task.get("entry_point") or ""

            start_time = time.perf_counter()

            # Execute coding loop
            res = await run_harness(
                task=f"Task: {prompt}\nTest code: {test_code}\nEntry Point: {entry_point}",
                allow_stub=self.allow_stub,
                config=HarnessConfig(
                    code_agent="benchmark-agent",
                    provider=self.provider,
                    model=self.model,
                    max_steps=3,
                ),
            )

            duration_ms = int((time.perf_counter() - start_time) * 1000)
            total_duration_ms += duration_ms
            total_tokens += getattr(res, "total_tokens", 0)
            total_cost += getattr(res, "estimated_cost", 0.0)

            is_solved = res.success
            if is_solved:
                solved += 1
            else:
                failed += 1

            self.results.append(
                {
                    "task_id": task_id,
                    "success": is_solved,
                    "duration_ms": duration_ms,
                    "tokens": getattr(res, "total_tokens", 0),
                    "cost": getattr(res, "estimated_cost", 0.0),
                    "error": res.error,
                }
            )

        total = len(tasks)
        accuracy = solved / total if total > 0 else 0.0
        pass_at_1 = accuracy

        summary = {
            "suite": os.path.basename(self.suite_path),
            "total_tasks": total,
            "solved": solved,
            "failed": failed,
            "accuracy": accuracy,
            "pass_at_1": pass_at_1,
            "duration_ms": total_duration_ms,
            "tokens": total_tokens,
            "estimated_cost": total_cost,
            "results": self.results,
        }
        return summary


def compare_benchmarks(
    current_summary: dict[str, Any], baseline_path: str, threshold: float = 0.05
) -> dict[str, Any]:
    if not os.path.exists(baseline_path):
        raise FileNotFoundError(f"Baseline file not found: {baseline_path}")
    with open(baseline_path) as f:
        baseline = json.load(f)

    current_acc = current_summary["accuracy"]
    baseline_acc = baseline.get("accuracy", 0.0)

    diff = current_acc - baseline_acc
    regressed = diff < -threshold

    return {
        "current_accuracy": current_acc,
        "baseline_accuracy": baseline_acc,
        "diff": diff,
        "regressed": regressed,
        "status": "fail" if regressed else "pass",
    }
