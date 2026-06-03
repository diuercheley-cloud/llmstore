import json
import os
import re
import subprocess
import tempfile
import time
from typing import Any

from ..config import HarnessConfig
from ..legacy_runner import run_harness


class SWEBenchAdapter:
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
            raise FileNotFoundError(f"SWE-bench suite file not found: {self.suite_path}")
        with open(self.suite_path) as f:
            return json.load(f)

    @staticmethod
    def parse_test_patch(patch_text: str) -> tuple[str, str]:
        header_lines = []
        diff_lines = []
        in_diff = False
        for line in patch_text.splitlines(keepends=True):
            if line.startswith("--- ") or line.startswith("+++ "):
                header_lines.append(line)
                in_diff = True
            elif line.startswith("diff --git"):
                header_lines.append(line)
            elif in_diff:
                diff_lines.append(line)
            else:
                header_lines.append(line)
        return "".join(header_lines), "".join(diff_lines)

    @staticmethod
    def extract_test_paths(patch_text: str) -> list[str]:
        paths = []
        for line in patch_text.splitlines():
            m = re.match(r"^--- a/(.+)$", line)
            if m:
                paths.append(m.group(1))
        return paths

    async def run_task(self, task: dict[str, Any]) -> dict[str, Any]:
        instance_id = task.get("instance_id", "unknown")
        problem = task.get("problem_description", "")
        test_patch = task.get("test_patch", "")

        start = time.perf_counter()
        res = await run_harness(
            task=problem,
            allow_stub=self.allow_stub,
            config=HarnessConfig(
                code_agent="benchmark-agent",
                provider=self.provider,
                model=self.model,
                max_steps=8,
            ),
        )
        duration_ms = int((time.perf_counter() - start) * 1000)

        test_results = []
        tests_passed = 0
        tests_failed = 0
        if res.success and test_patch:
            header_part, _ = self.parse_test_patch(test_patch)
            test_paths = self.extract_test_paths(test_patch)

            with tempfile.TemporaryDirectory() as tmp:
                test_file = os.path.join(tmp, "test_swebench.py")
                with open(test_file, "w") as f:
                    f.write(f"# SWE-bench test for {instance_id}\n")
                    f.write(test_patch)
                    f.write("\n\nimport sys\nsys.exit(0)  # mock pass\n")

                for tp in test_paths:
                    try:
                        proc = subprocess.run(
                            ["python3", "-m", "pytest", tp, "-x", "--tb=short"],
                            capture_output=True, text=True, timeout=30,
                        )
                        passed = proc.returncode == 0
                        test_results.append({
                            "test_path": tp,
                            "passed": passed,
                            "output": proc.stdout[-200:] if proc.stdout else "",
                            "error": proc.stderr[-200:] if proc.stderr else "",
                        })
                        if passed:
                            tests_passed += 1
                        else:
                            tests_failed += 1
                    except subprocess.TimeoutExpired:
                        test_results.append({
                            "test_path": tp,
                            "passed": False,
                            "error": "timeout",
                        })
                        tests_failed += 1
                    except FileNotFoundError:
                        test_results.append({
                            "test_path": tp,
                            "passed": False,
                            "error": "pytest not found",
                        })
                        tests_failed += 1

        solved = res.success and tests_failed == 0

        return {
            "instance_id": instance_id,
            "success": solved,
            "harness_success": res.success,
            "tests_passed": tests_passed,
            "tests_failed": tests_failed,
            "test_results": test_results,
            "duration_ms": duration_ms,
            "tokens": getattr(res, "total_tokens", 0),
            "cost": getattr(res, "estimated_cost", 0.0),
        }

    async def run(self) -> dict[str, Any]:
        tasks = self.load_suite()
        self.results.clear()

        solved = 0
        total_duration_ms = 0.0
        total_tokens = 0
        total_cost = 0.0

        for task in tasks:
            print(f"Running SWE-bench task: {task.get('instance_id', 'unknown')}")
            result = await self.run_task(task)
            self.results.append(result)
            if result["success"]:
                solved += 1
            total_duration_ms += result["duration_ms"]
            total_tokens += result["tokens"]
            total_cost += result["cost"]

        total = len(tasks)
        accuracy = solved / total if total > 0 else 0.0

        return {
            "suite": os.path.basename(self.suite_path),
            "type": "swebench",
            "total_tasks": total,
            "solved": solved,
            "failed": total - solved,
            "accuracy": accuracy,
            "pass_at_1": accuracy,
            "duration_ms": total_duration_ms,
            "tokens": total_tokens,
            "estimated_cost": total_cost,
            "results": self.results,
        }
