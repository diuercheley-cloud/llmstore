#!/usr/bin/env python3
# scripts/dev/benchmark-llm-harness.py
"""
Performance benchmark for LLM Harness.
Runs coding loops with mocked OpenAI-compatible HTTP responses to measure latencies.
"""

import argparse
import asyncio
import json
import os
import shutil
import sys
import tempfile
import time
from typing import Any
from unittest.mock import patch

import httpx

# Ensure project modules are importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.llm_harness.agent_client import AgentClient
from scripts.llm_harness.coding_loop import CodingLoop
from scripts.llm_harness.reporter import Reporter
from scripts.llm_harness.workspace import Workspace

RESPONSES = [
    # 1. Plan
    {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "type": "plan",
                            "reason": "Identify and fix addition bug",
                            "payload": {"message": "I will read app.py and fix the bug"},
                        }
                    ),
                }
            }
        ],
        "usage": {"total_tokens": 100},
    },
    # 2. Read File
    {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "type": "read_file",
                            "reason": "Need to see the code",
                            "payload": {"path": "app.py"},
                        }
                    ),
                }
            }
        ],
        "usage": {"total_tokens": 100},
    },
    # 3. Apply Patch
    {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "type": "apply_patch",
                            "reason": "Correcting subtraction to addition",
                            "payload": {
                                "diff": "--- app.py\n+++ app.py\n@@ -1,2 +1,2 @@\n def add(a, b):\n-    return a - b\n+    return a + b\n"
                            },
                        }
                    ),
                }
            }
        ],
        "usage": {"total_tokens": 100},
    },
    # 4. Run Tests
    {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "type": "run_tests",
                            "reason": "Verify the fix",
                            "payload": {"test_path": "tests/test_app.py"},
                        }
                    ),
                }
            }
        ],
        "usage": {"total_tokens": 100},
    },
    # 5. Final
    {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "type": "final",
                            "reason": "Verified and fixed",
                            "payload": {"message": "Bug fixed successfully"},
                        }
                    ),
                }
            }
        ],
        "usage": {"total_tokens": 100},
    },
]


class MockTransport(httpx.AsyncBaseTransport):
    def __init__(self, responses: list[dict[str, Any]]):
        self.responses = responses
        self.count = 0

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if self.count >= len(self.responses):
            resp_data = self.responses[-1]
        else:
            resp_data = self.responses[self.count]
            self.count += 1

        return httpx.Response(
            200,
            content=json.dumps(resp_data).encode(),
            headers={"Content-Type": "application/json"},
        )


async def run_iteration(index: int) -> dict[str, Any]:
    tmp_dir = tempfile.mkdtemp()
    try:
        app_file = os.path.join(tmp_dir, "app.py")
        with open(app_file, "w") as f:
            f.write("def add(a, b):\n    return a - b\n")

        tests_dir = os.path.join(tmp_dir, "tests")
        os.makedirs(tests_dir)
        test_file = os.path.join(tests_dir, "test_app.py")
        with open(test_file, "w") as f:
            f.write("from app import add\ndef test_add():\n    assert add(1, 2) == 3\n")

        transport = MockTransport(RESPONSES)
        os.environ["MOCK_API_KEY"] = "sk-test-key"
        os.environ["PYTHONPATH"] = f".:{os.environ.get('PYTHONPATH', '')}"

        agent_client = AgentClient(
            agent_id=f"benchmark-agent-{index}",
            provider="openai-compatible",
            base_url="http://mock-llm",
            model="gpt-4",
            api_key_env="MOCK_API_KEY",
        )

        async with Workspace(base_path=tmp_dir) as ws:
            from httpx import AsyncClient as RealAsyncClient

            def mock_client_factory(**kwargs):
                kwargs.pop("transport", None)
                return RealAsyncClient(transport=transport, **kwargs)

            with patch("httpx.AsyncClient", side_effect=mock_client_factory):
                loop = CodingLoop(
                    agent_client=agent_client, workspace=ws, max_steps=10, test_command="pytest"
                )

                # Start measuring total loop time
                start_loop = time.time()
                result = await loop.run(task="Fix the bug in app.py")
                total_loop_time_ms = (time.time() - start_loop) * 1000

                # Extract action timings from result events
                apply_patch_time_ms = 0.0
                run_tests_time_ms = 0.0
                step_durations = []

                for e in result.events:
                    if e.get("event") == "action.completed":
                        duration = e.get("duration_ms", 0.0)
                        step_durations.append(duration)
                        if e.get("action_type") == "apply_patch":
                            apply_patch_time_ms = duration
                        elif e.get("action_type") == "run_tests":
                            run_tests_time_ms = duration

                avg_time_per_step_ms = (
                    sum(step_durations) / len(step_durations) if step_durations else 0.0
                )

                # Measure reporter overhead
                reporter = Reporter(output_dir=tmp_dir)
                start_reporter = time.time()
                _ = reporter.generate_summary(
                    result,
                    trace=result.events,
                    policy_info={"provider": "openai-compatible"},
                )
                _ = reporter.generate_markdown_report(
                    result,
                    blocked_actions=[],
                    provider="openai-compatible",
                )
                reporter_overhead_ms = (time.time() - start_reporter) * 1000

                return {
                    "iteration": index,
                    "total_time_ms": total_loop_time_ms,
                    "avg_time_per_step_ms": avg_time_per_step_ms,
                    "apply_patch_time_ms": apply_patch_time_ms,
                    "run_tests_time_ms": run_tests_time_ms,
                    "reporter_overhead_ms": reporter_overhead_ms,
                }
    finally:
        shutil.rmtree(tmp_dir)
        if "MOCK_API_KEY" in os.environ:
            del os.environ["MOCK_API_KEY"]


async def main():
    parser = argparse.ArgumentParser(description="Run LLM Harness performance benchmark")
    parser.add_argument(
        "--iterations", type=int, default=3, help="Number of benchmark iterations to run"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="artifacts/benchmarks/llm-harness",
        help="Directory where benchmarks results are saved",
    )
    parser.add_argument(
        "--compare-baseline", action="store_true", help="Compare current results against baseline"
    )
    parser.add_argument(
        "--max-regression-percent",
        type=float,
        default=10.0,
        help="Maximum allowed regression percentage",
    )
    args = parser.parse_args()

    print(f"Starting benchmark of LLM Harness with {args.iterations} iterations...")

    results = []
    for i in range(args.iterations):
        print(f"Running iteration {i + 1}/{args.iterations}...")
        res = await run_iteration(i + 1)
        results.append(res)

    # Compute stats
    def get_mean(key: str) -> float:
        return sum(r[key] for r in results) / len(results)

    total_time_mean = get_mean("total_time_ms")
    avg_step_mean = get_mean("avg_time_per_step_ms")
    apply_patch_mean = get_mean("apply_patch_time_ms")
    run_tests_mean = get_mean("run_tests_time_ms")
    reporter_overhead_mean = get_mean("reporter_overhead_ms")

    # Output JSON structure
    benchmark_data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "iterations_count": args.iterations,
        "summary": {
            "total_time_ms": {"mean": total_time_mean},
            "avg_time_per_step_ms": {"mean": avg_step_mean},
            "apply_patch_time_ms": {"mean": apply_patch_mean},
            "run_tests_time_ms": {"mean": run_tests_mean},
            "reporter_overhead_ms": {"mean": reporter_overhead_mean},
        },
        "iterations": results,
    }

    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)

    json_path = os.path.join(args.output_dir, "latest.json")
    json_str = json.dumps(benchmark_data, indent=2)
    # Double check and redact secrets
    json_str = json_str.replace("sk-test-key", "REDACTED")
    with open(json_path, "w") as f:
        f.write(json_str)

    # Output Markdown format
    md_lines = [
        "# LLM Harness Performance Benchmark Report",
        "",
        f"**Date**: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
        f"**Iterations**: {args.iterations}",
        "",
        "## Aggregated Metrics (Averages)",
        "",
        "| Metric | Average Value |",
        "| :--- | :--- |",
        f"| **Total execution time** | {total_time_mean:.2f} ms |",
        f"| **Average time per step** | {avg_step_mean:.2f} ms |",
        f"| **apply_patch execution time** | {apply_patch_mean:.2f} ms |",
        f"| **run_tests execution time** | {run_tests_mean:.2f} ms |",
        f"| **Reporter overhead** | {reporter_overhead_mean:.2f} ms |",
        "",
        "## Iterations breakdown",
        "",
    ]

    header_line = "| Iteration | Total Time (ms) | Avg Step Time (ms) | apply_patch Time (ms) | run_tests Time (ms) | Reporter Overhead (ms) |"
    sep_line = "| :--- | :--- | :--- | :--- | :--- | :--- |"
    md_lines.extend([header_line, sep_line])

    for r in results:
        md_lines.append(
            f"| {r['iteration']} | {r['total_time_ms']:.2f} | {r['avg_time_per_step_ms']:.2f} | "
            f"{r['apply_patch_time_ms']:.2f} | {r['run_tests_time_ms']:.2f} | {r['reporter_overhead_ms']:.2f} |"
        )

    md_str = "\n".join(md_lines)
    # Double check and redact secrets
    md_str = md_str.replace("sk-test-key", "REDACTED")

    md_path = os.path.join(args.output_dir, "latest.md")
    with open(md_path, "w") as f:
        f.write(md_str)

    print("\nBenchmark results summary:")
    print(f"Total time average: {total_time_mean:.2f} ms")
    print(f"Avg step time average: {avg_step_mean:.2f} ms")
    print(f"apply_patch average: {apply_patch_mean:.2f} ms")
    print(f"run_tests average: {run_tests_mean:.2f} ms")
    print(f"Reporter overhead average: {reporter_overhead_mean:.2f} ms")
    print(f"\nSaved JSON report to {json_path}")
    print(f"Saved Markdown report to {md_path}")

    # Compare with baseline if requested
    if args.compare_baseline:
        baseline_path = os.path.join(args.output_dir, "baseline.json")
        if os.path.exists(baseline_path):
            try:
                with open(baseline_path) as f:
                    baseline_data = json.load(f)
                baseline_time = baseline_data["summary"]["total_time_ms"]["mean"]
                regression = ((total_time_mean - baseline_time) / baseline_time) * 100
                print(f"\nComparing against baseline total_time_ms: {baseline_time:.2f} ms")
                print(f"Current total_time_ms: {total_time_mean:.2f} ms")
                print(f"Performance Change: {regression:.2f}%")
                if regression > args.max_regression_percent:
                    print(
                        f"ERROR: Regression threshold of {args.max_regression_percent}% exceeded!",
                        file=sys.stderr,
                    )
                    sys.exit(1)
                else:
                    print("SUCCESS: Performance is within acceptable regression threshold.")
            except Exception as e:
                print(f"WARNING: Failed to read or parse baseline.json: {e}", file=sys.stderr)
        else:
            print(f"WARNING: Baseline file not found at {baseline_path}. Skipping comparison.")


if __name__ == "__main__":
    asyncio.run(main())
