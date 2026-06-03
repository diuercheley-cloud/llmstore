import time
from typing import Any


class MetricsManager:
    """
    Manages internal metrics for LLM harness runs.
    """

    def __init__(self):
        self.runs_total = 0
        self.runs_failed = 0
        self.llm_calls_total = 0
        self.tool_calls_total = 0
        self.tokens_total = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.estimated_cost_total = 0.0
        self.cache_hits = 0
        self.cache_misses = 0
        self.duration_ms = 0.0
        self.start_time = 0.0
        self.changed_files: list[str] = []

    def start_run(self):
        self.runs_total += 1
        self.start_time = time.perf_counter()

    def end_run(self, success: bool):
        if not success:
            self.runs_failed += 1
        if self.start_time > 0:
            self.duration_ms = (time.perf_counter() - self.start_time) * 1000

    def record_llm_call(
        self, tokens: int, prompt_tokens: int = 0, completion_tokens: int = 0, cost: float = 0.0
    ):
        self.llm_calls_total += 1
        self.tokens_total += tokens
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        self.estimated_cost_total += cost

    def record_tool_call(self, cached: bool = False):
        self.tool_calls_total += 1
        if cached:
            self.cache_hits += 1
        else:
            self.cache_misses += 1

    def record_changed_files(self, files: list[str]):
        self.changed_files = list(set(self.changed_files + files))

    def to_dict(self) -> dict[str, Any]:
        return {
            "runs_total": self.runs_total,
            "runs_failed": self.runs_failed,
            "llm_calls_total": self.llm_calls_total,
            "tool_calls_total": self.tool_calls_total,
            "tokens_total": self.tokens_total,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "estimated_cost_total": round(self.estimated_cost_total, 6),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "duration_ms": round(self.duration_ms, 2),
            "changed_files": self.changed_files,
        }
