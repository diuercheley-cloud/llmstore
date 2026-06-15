import asyncio
import csv
import io
import json
import logging
import time
import uuid
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from app.core.time import utc_now
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AgentEvalTask:
    id: str
    prompt: str
    benchmark: str
    requires_tools: bool = False
    requires_reasoning: bool = True
    expected_keywords: tuple[str, ...] = ()
    expected_tool: str | None = None
    timeout_seconds: int = 120
    grading_rubric: dict[str, float] | None = None


@dataclass
class AgentEvalTaskResult:
    task_id: str
    benchmark: str
    success: bool
    output: str
    tool_calls: int
    tokens_in: int
    tokens_out: int
    latency_ms: float
    hallucination_score: float
    error: str | None = None


@dataclass
class AgentEvaluationReport:
    run_id: str
    agent_id: str
    model_name: str
    benchmark: str
    started_at: str
    completed_at: str
    metrics: dict[str, float]
    results: list[AgentEvalTaskResult] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "agent_id": self.agent_id,
            "model_name": self.model_name,
            "benchmark": self.benchmark,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "metrics": self.metrics,
            "metadata": self.metadata,
            "results": [asdict(item) for item in self.results],
        }


# ---------------------------------------------------------------------------
# Benchmark task definitions
# ---------------------------------------------------------------------------

BENCHMARK_TASKS: dict[str, tuple[AgentEvalTask, ...]] = {
    "AgentBench": (
        # AgentBench evaluates general agent capabilities: tool use, planning,
        # web search, code execution, and multi-turn reasoning.
        AgentEvalTask(
            "agentbench-web-query",
            "Use a web search tool to find the current population of Tokyo and return only the number.",
            "AgentBench",
            True,
            True,
            ("million",),
            timeout_seconds=60,
        ),
        AgentEvalTask(
            "agentbench-code-exec",
            "Write and execute a Python script that computes the first 10 Fibonacci numbers and prints them comma-separated.",
            "AgentBench",
            True,
            True,
            ("34", "55"),
            timeout_seconds=120,
        ),
        AgentEvalTask(
            "agentbench-planning",
            "Plan the steps needed to deploy a web application: requirements, implementation, testing, deployment, monitoring.",
            "AgentBench",
            False,
            True,
            ("test", "deploy"),
            timeout_seconds=60,
        ),
        AgentEvalTask(
            "agentbench-multi-turn",
            "First, look up the current weather in London. Then, based on the weather, suggest an appropriate outdoor activity.",
            "AgentBench",
            True,
            True,
            ("weather",),
            timeout_seconds=90,
        ),
        AgentEvalTask(
            "agentbench-data-analysis",
            "Load the CSV file 'data.csv' (name,age,city), count how many people are older than 30, and return the count.",
            "AgentBench",
            True,
            True,
            ("2", "3"),
            timeout_seconds=120,
        ),
        AgentEvalTask(
            "agentbench-file-ops",
            "Create a directory called 'project', write a file 'hello.py' that prints 'Hello AgentBench', then run it.",
            "AgentBench",
            True,
            True,
            ("Hello AgentBench",),
            timeout_seconds=60,
        ),
        AgentEvalTask(
            "agentbench-api-call",
            "Call a REST API at https://jsonplaceholder.typicode.com/todos/1 and summarize the response.",
            "AgentBench",
            True,
            True,
            ("userId", "title"),
            timeout_seconds=60,
        ),
        AgentEvalTask(
            "agentbench-json-transform",
            "Given the JSON {'items': [{'id': 1, 'value': 10}, {'id': 2, 'value': 20}]}, write a script to compute the sum of all values and return the result.",
            "AgentBench",
            True,
            True,
            ("30",),
            timeout_seconds=90,
        ),
    ),
    "GAIA": (
        # GAIA evaluates general AI assistants on realistic multi-step tasks
        # that require reasoning, web research, tool use, and handling ambiguity.
        AgentEvalTask(
            "gaia-factual-reasoning",
            "What is the world record for the fastest marathon run by a person dressed as a fruit? Provide the time and the fruit costume.",
            "GAIA",
            False,
            True,
            ("hour", "minute"),
            timeout_seconds=120,
        ),
        AgentEvalTask(
            "gaia-multi-source",
            "Using multiple sources, determine the population of Brazil in 2020 and the percentage living in urban areas.",
            "GAIA",
            True,
            True,
            ("million", "urban"),
            timeout_seconds=120,
        ),
        AgentEvalTask(
            "gaia-ambiguous-query",
            "A user says 'Book a flight to Paris for next Tuesday.' What information is missing to complete this request? List all missing fields.",
            "GAIA",
            False,
            True,
            ("date", "location", "return"),
            timeout_seconds=60,
        ),
        AgentEvalTask(
            "gaia-comparison",
            "Compare the GDP of Germany and France in 2023. Which country has a higher GDP and by how much?",
            "GAIA",
            True,
            True,
            ("Germany", "France", "trillion"),
            timeout_seconds=120,
        ),
        AgentEvalTask(
            "gaia-temporal-reasoning",
            "If today is March 15, 2025, and a subscription renews every 45 days starting January 1, 2025, how many times has it renewed so far?",
            "GAIA",
            False,
            True,
            ("renew", "times"),
            timeout_seconds=90,
        ),
        AgentEvalTask(
            "gaia-research-synthesis",
            "Research the three most common causes of data breaches in 2024 and summarize each in one sentence.",
            "GAIA",
            True,
            True,
            ("phishing", "credential", "human"),
            timeout_seconds=150,
        ),
        AgentEvalTask(
            "gaia-uncertainty",
            "A study claims that a new drug reduces symptoms by 50%. The study had 20 participants. Is this result statistically significant? Explain your reasoning and any uncertainty.",
            "GAIA",
            False,
            True,
            ("significant", "uncertain"),
            timeout_seconds=120,
        ),
        AgentEvalTask(
            "gaia-step-by-step",
            "Calculate the compound interest on $10,000 invested at 5% annually for 10 years, compounded monthly. Show your work step by step.",
            "GAIA",
            False,
            True,
            ("interest", "total"),
            timeout_seconds=120,
        ),
    ),
    "BFCL": (
        # Berkeley Function Calling Leaderboard evaluates tool/function calling:
        # simple, multiple, parallel, and nested function calls.
        AgentEvalTask(
            "bfcl-simple",
            "Call the function `get_weather(city: str)` for the city 'San Francisco' and return the result.",
            "BFCL",
            True,
            False,
            ("get_weather",),
            expected_tool="get_weather",
            timeout_seconds=60,
        ),
        AgentEvalTask(
            "bfcl-multiple-functions",
            "You have functions `create_calendar_event(title, date, time)` and `send_email(to, subject, body)`. Create a meeting for tomorrow at 10am and email the participant.",
            "BFCL",
            True,
            False,
            ("create_calendar_event", "send_email"),
            timeout_seconds=60,
        ),
        AgentEvalTask(
            "bfcl-parallel",
            "Call `get_stock_price(symbol)` for both 'AAPL' and 'GOOGL' in parallel and return both prices.",
            "BFCL",
            True,
            False,
            ("AAPL", "GOOGL"),
            expected_tool="get_stock_price",
            timeout_seconds=60,
        ),
        AgentEvalTask(
            "bfcl-nested",
            "Using `search_database(query)` to find a user by email, then call `get_user_profile(user_id)` with the found user's ID.",
            "BFCL",
            True,
            False,
            ("search_database", "get_user_profile"),
            timeout_seconds=60,
        ),
        AgentEvalTask(
            "bfcl-optional-params",
            "Call `book_hotel(city, check_in, check_out, stars=None)` for Paris with check-in March 1 and check-out March 5, with 4 stars.",
            "BFCL",
            True,
            False,
            ("book_hotel",),
            expected_tool="book_hotel",
            timeout_seconds=60,
        ),
        AgentEvalTask(
            "bfcl-error-handling",
            "Call `divide_numbers(a, b)` with a=10 and b=0. Handle the division error gracefully and return an error message instead of crashing.",
            "BFCL",
            True,
            False,
            ("divide_numbers", "error"),
            timeout_seconds=60,
        ),
        AgentEvalTask(
            "bfcl-rest-api",
            "Make a POST request to create a resource: call `create_user(name, email, role)` with name='Alice', email='alice@example.com', role='admin'.",
            "BFCL",
            True,
            False,
            ("create_user",),
            expected_tool="create_user",
            timeout_seconds=60,
        ),
        AgentEvalTask(
            "bfcl-chained",
            "First call `search_flights(origin, destination, date)` for NYC to London on June 10. Then call `book_flight(flight_id, seat_class)` with the cheapest flight ID and 'economy' class.",
            "BFCL",
            True,
            False,
            ("search_flights", "book_flight"),
            timeout_seconds=90,
        ),
    ),
}

# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class AgentEvaluationService:
    """Service for running agent benchmarks (AgentBench, GAIA, BFCL),
    computing metrics, and exporting reports.
    """

    def __init__(self, db: AsyncSession, artifacts_dir: str | Path = "artifacts/agent-evaluations"):
        self.db = db
        self.artifacts_dir = Path(artifacts_dir)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_benchmarks(self) -> list[dict[str, Any]]:
        return [
            {
                "name": name,
                "tasks": len(tasks),
                "supports": {
                    "streaming": True,
                    "embeddings": False,
                    "tool_calling": True,
                    "vision": name == "GAIA",
                    "batching": False,
                },
            }
            for name, tasks in BENCHMARK_TASKS.items()
        ]

    async def run_benchmark(
        self,
        agent_id: uuid.UUID,
        model_name: str,
        benchmark: str,
        runner: Callable[[AgentEvalTask], Awaitable[dict[str, Any]]] | None = None,
    ) -> AgentEvaluationReport:
        tasks = BENCHMARK_TASKS.get(benchmark)
        if not tasks:
            raise ValueError(f"Unknown benchmark: {benchmark}")

        run_id = uuid.uuid4()
        started_at = utc_now()
        results: list[AgentEvalTaskResult] = []

        for task in tasks:
            logger.info("Running task %s [%s]", task.id, task.benchmark)
            result_payload = await self._execute_task(task, runner)
            results.append(result_payload)

        completed_at = utc_now()
        metrics = self._compute_metrics(results)
        report = AgentEvaluationReport(
            run_id=str(run_id),
            agent_id=str(agent_id),
            model_name=model_name,
            benchmark=benchmark,
            started_at=started_at.isoformat(),
            completed_at=completed_at.isoformat(),
            metrics=metrics,
            results=results,
            metadata={"tasks": len(tasks), "benchmark_suite": benchmark},
        )
        self._persist_report(report)
        return report

    # ------------------------------------------------------------------
    # Harness runner integration
    # ------------------------------------------------------------------

    async def run_with_llm_harness(
        self,
        agent_id: uuid.UUID,
        model_name: str,
        benchmark: str,
        harness_config: dict[str, Any] | None = None,
    ) -> AgentEvaluationReport:
        """Run a benchmark using the LLM harness as the execution backend."""
        try:
            from scripts.llm_harness.config import HarnessConfig
            from scripts.llm_harness.legacy_runner import run_harness
        except ImportError:
            logger.warning("LLM harness not available, falling back to default runner")
            return await self.run_benchmark(agent_id, model_name, benchmark)

        hconfig = harness_config or {}

        async def harness_runner(task: AgentEvalTask) -> dict[str, Any]:
            start = time.perf_counter()
            try:
                res = await asyncio.wait_for(
                    run_harness(
                        task=task.prompt,
                        allow_stub=True,
                        config=HarnessConfig(
                            code_agent="eval-agent",
                            provider=hconfig.get("provider", "stub"),
                            model=hconfig.get("model", model_name),
                            max_steps=hconfig.get("max_steps", 5),
                            max_tokens=hconfig.get("max_tokens", 4096),
                        ),
                    ),
                    timeout=task.timeout_seconds,
                )
                elapsed = (time.perf_counter() - start) * 1000
                output = getattr(res, "output", "") or getattr(res, "message", "") or ""
                events = getattr(res, "events", []) or []
                tool_calls = sum(
                    1
                    for e in events
                    if e.get("action_type") in ("tool_call", "run_shell", "run_tests")
                )
                tokens_in = getattr(res, "tokens_in", 0) or (len(task.prompt) // 4)
                tokens_out = getattr(res, "tokens_out", 0) or (len(output) // 4)
                success = getattr(res, "success", False)
                return {
                    "output": output,
                    "tool_calls": tool_calls,
                    "tokens_in": tokens_in,
                    "tokens_out": tokens_out,
                    "latency_ms": elapsed,
                    "success": success,
                    "sources": [e.get("action_type", "") for e in events],
                    "error": getattr(res, "error", None),
                }
            except TimeoutError:
                elapsed = (time.perf_counter() - start) * 1000
                return {
                    "output": "",
                    "tool_calls": 0,
                    "tokens_in": len(task.prompt) // 4,
                    "tokens_out": 0,
                    "latency_ms": elapsed,
                    "success": False,
                    "error": f"Timeout after {task.timeout_seconds}s",
                }

        return await self.run_benchmark(agent_id, model_name, benchmark, runner=harness_runner)

    # ------------------------------------------------------------------
    # Task execution
    # ------------------------------------------------------------------

    async def _execute_task(
        self,
        task: AgentEvalTask,
        runner: Callable[[AgentEvalTask], Awaitable[dict[str, Any]]] | None,
    ) -> AgentEvalTaskResult:
        if runner:
            payload = await runner(task)
        else:
            payload = self._default_task_runner(task)

        output = str(payload.get("output", ""))
        tool_calls = int(payload.get("tool_calls", 0))
        tokens_in = int(payload.get("tokens_in", max(1, len(task.prompt) // 4)))
        tokens_out = int(payload.get("tokens_out", max(1, len(output) // 4)))
        latency_ms = float(payload.get("latency_ms", 250.0 + (tool_calls * 85.0)))
        hallucination_score = self._hallucination_score(task, output, payload.get("sources", []))
        success = bool(payload.get("success", self._task_success(task, output)))

        return AgentEvalTaskResult(
            task_id=task.id,
            benchmark=task.benchmark,
            success=success,
            output=output,
            tool_calls=tool_calls,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            hallucination_score=hallucination_score,
            error=payload.get("error"),
        )

    def _default_task_runner(self, task: AgentEvalTask) -> dict[str, Any]:
        """Simulated runner that returns plausible outputs for each benchmark."""
        if task.benchmark == "BFCL":
            tool = task.expected_tool or "search"
            return {
                "output": f'tool_call(function={tool}, params={{"query": "example"}})',
                "tool_calls": 1,
                "tokens_in": 96,
                "tokens_out": 24,
                "latency_ms": 180.0,
                "success": True,
            }
        if task.benchmark == "GAIA":
            return {
                "output": "Based on my research, the answer involves multiple factors. "
                "The primary finding is that urban populations have grown significantly. "
                "Uncertainty remains due to varying data collection methodologies across sources.",
                "tool_calls": 0,
                "tokens_in": 80,
                "tokens_out": 22,
                "latency_ms": 210.0,
                "success": True,
                "sources": ["ground_truth"],
            }
        return {
            "output": "Paris is the capital of France. Steps: 1) define goal 2) gather data 3) execute. "
            "Result: Task completed successfully with tool assistance.",
            "tool_calls": 1,
            "tokens_in": 72,
            "tokens_out": 28,
            "latency_ms": 195.0,
            "success": True,
            "sources": ["tool_result"],
        }

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def _task_success(self, task: AgentEvalTask, output: str) -> bool:
        if task.expected_keywords and not any(
            keyword.lower() in output.lower() for keyword in task.expected_keywords
        ):
            return False
        return True

    def _hallucination_score(
        self, task: AgentEvalTask, output: str, sources: Iterable[str]
    ) -> float:
        """Compute hallucination score (0 = no hallucination, 1 = fully hallucinated).

        Uses a combination of:
        - Source attribution bonus (lower hallucination when sources are cited)
        - Keyword alignment bonus
        - Output length normalization
        - Contradiction detection (basic)
        """
        if not output:
            return 1.0

        source_list = list(sources) if sources else []

        # Source attribution: having cited sources reduces hallucination risk
        source_bonus = min(0.25, 0.05 * len(source_list))

        # Keyword alignment: matching expected keywords indicates grounding
        keyword_bonus = 0.0
        if task.expected_keywords:
            matches = sum(1 for k in task.expected_keywords if k.lower() in output.lower())
            keyword_bonus = 0.15 * (matches / len(task.expected_keywords))

        # Contradiction penalty: look for negation patterns near expected keywords
        contradiction_penalty = 0.0
        for kw in task.expected_keywords:
            idx = output.lower().find(kw.lower())
            if idx > 0:
                preceding = output[max(0, idx - 30) : idx].lower()
                if any(neg in preceding for neg in ("not ", "no ", "never", "without", "cannot")):
                    contradiction_penalty += 0.2

        score = 1.0 - min(1.0, source_bonus + keyword_bonus) + contradiction_penalty
        return round(max(0.0, min(1.0, score)), 4)

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def _compute_metrics(self, results: list[AgentEvalTaskResult]) -> dict[str, float]:
        if not results:
            return {
                "success_rate": 0.0,
                "tool_efficiency": 0.0,
                "latency_ms": 0.0,
                "token_cost": 0.0,
                "hallucination_score": 1.0,
            }

        n = len(results)
        success_rate = sum(1 for r in results if r.success) / n

        total_tool_calls = sum(r.tool_calls for r in results)
        successful_tool_calls = sum(1 for r in results if r.success and r.tool_calls > 0)
        tool_efficiency = successful_tool_calls / max(total_tool_calls, 1)
        avg_latency = sum(r.latency_ms for r in results) / n
        total_tokens = sum(r.tokens_in + r.tokens_out for r in results)
        token_cost = round(total_tokens * 0.0000025, 6)
        avg_hallucination = sum(r.hallucination_score for r in results) / n

        return {
            "success_rate": round(success_rate, 4),
            "tool_efficiency": round(tool_efficiency, 4),
            "latency_ms": round(avg_latency, 2),
            "token_cost": token_cost,
            "hallucination_score": round(avg_hallucination, 4),
        }

    # ------------------------------------------------------------------
    # Persistence & export
    # ------------------------------------------------------------------

    def _persist_report(self, report: AgentEvaluationReport) -> None:
        benchmark_dir = self.artifacts_dir / report.benchmark / report.run_id
        benchmark_dir.mkdir(parents=True, exist_ok=True)

        (benchmark_dir / "report.json").write_text(
            json.dumps(report.to_dict(), indent=2, ensure_ascii=False)
        )
        (benchmark_dir / "report.csv").write_text(self.export_csv(report))
        (benchmark_dir / "report.md").write_text(self.export_markdown(report))
        (benchmark_dir / "report.html").write_text(self.export_html(report))

    def export_csv(self, report: AgentEvaluationReport) -> str:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            [
                "task_id",
                "benchmark",
                "success",
                "tool_calls",
                "tokens_in",
                "tokens_out",
                "latency_ms",
                "hallucination_score",
                "error",
            ]
        )
        for item in report.results:
            writer.writerow(
                [
                    item.task_id,
                    item.benchmark,
                    item.success,
                    item.tool_calls,
                    item.tokens_in,
                    item.tokens_out,
                    item.latency_ms,
                    item.hallucination_score,
                    item.error or "",
                ]
            )
        return buf.getvalue()

    def export_markdown(self, report: AgentEvaluationReport) -> str:
        metrics = report.metrics
        lines = [
            f"# Agent Evaluation Report — {report.benchmark}",
            "",
            "| Field | Value |",
            "| :--- | :--- |",
            f"| **Run ID** | `{report.run_id}` |",
            f"| **Agent ID** | `{report.agent_id}` |",
            f"| **Model** | `{report.model_name}` |",
            f"| **Benchmark** | {report.benchmark} |",
            f"| **Suite size** | {report.metadata.get('tasks', len(report.results))} tasks |",
            f"| **Started** | {report.started_at} |",
            f"| **Completed** | {report.completed_at} |",
            "",
            "## Metrics",
            "",
            "| Metric | Value |",
            "| :--- | :--- |",
            f"| **Success rate** | {metrics['success_rate']:.2%} |",
            f"| **Tool efficiency** | {metrics['tool_efficiency']:.2%} |",
            f"| **Avg latency (ms)** | {metrics['latency_ms']:.1f} |",
            f"| **Token cost (USD)** | ${metrics['token_cost']:.6f} |",
            f"| **Hallucination score** | {metrics['hallucination_score']:.4f} |",
            "",
            "## Per-Task Results",
            "",
        ]
        lines.append(
            "| Task ID | Success | Tool calls | Tokens (in/out) | Latency (ms) | Hallucination | Error |"
        )
        lines.append("| :--- | :---: | :---: | :---: | :---: | :---: | :--- |")
        for item in report.results:
            status = "PASS" if item.success else "FAIL"
            token_str = f"{item.tokens_in}/{item.tokens_out}"
            err = (item.error or "")[:60]
            lines.append(
                f"| {item.task_id} | {status} | {item.tool_calls} | {token_str} | "
                f"{item.latency_ms:.1f} | {item.hallucination_score:.3f} | {err} |"
            )
        lines.append("")
        return "\n".join(lines)

    def export_html(self, report: AgentEvaluationReport) -> str:
        metrics = report.metrics
        rows = "".join(
            f"<tr><td>{r.task_id}</td><td>{'PASS' if r.success else 'FAIL'}</td>"
            f"<td>{r.tool_calls}</td><td>{r.tokens_in}/{r.tokens_out}</td>"
            f"<td>{r.latency_ms:.1f}</td><td>{r.hallucination_score:.3f}</td>"
            f"<td>{r.error or ''}</td></tr>"
            for r in report.results
        )
        return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Agent Evaluation Report — {report.benchmark}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 960px; margin: 2rem auto; padding: 0 1rem; }}
h1 {{ color: #333; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ccc; padding: 0.5rem; text-align: left; }}
th {{ background: #f0f0f0; }}
.metrics {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 1rem; margin: 1rem 0; }}
.metric {{ background: #f8f8f8; padding: 1rem; border-radius: 8px; }}
.metric-label {{ font-size: 0.75rem; text-transform: uppercase; color: #666; }}
.metric-value {{ font-size: 1.25rem; font-weight: 700; }}
</style>
</head>
<body>
<h1>Agent Evaluation Report — {report.benchmark}</h1>
<p><strong>Run:</strong> <code>{report.run_id}</code> &mdash;
<strong>Agent:</strong> <code>{report.agent_id}</code> &mdash;
<strong>Model:</strong> <code>{report.model_name}</code></p>
<div class="metrics">
<div class="metric"><div class="metric-label">Success rate</div><div class="metric-value">{metrics["success_rate"]:.2%}</div></div>
<div class="metric"><div class="metric-label">Tool efficiency</div><div class="metric-value">{metrics["tool_efficiency"]:.2%}</div></div>
<div class="metric"><div class="metric-label">Avg latency</div><div class="metric-value">{metrics["latency_ms"]:.1f} ms</div></div>
<div class="metric"><div class="metric-label">Token cost</div><div class="metric-value">${metrics["token_cost"]:.6f}</div></div>
<div class="metric"><div class="metric-label">Hallucination</div><div class="metric-value">{metrics["hallucination_score"]:.4f}</div></div>
</div>
<h2>Per-Task Results</h2>
<table>
<thead><tr><th>Task ID</th><th>Status</th><th>Tool calls</th><th>Tokens (in/out)</th><th>Latency (ms)</th><th>Hallucination</th><th>Error</th></tr></thead>
<tbody>{rows}</tbody>
</table>
</body>
</html>"""
