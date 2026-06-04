import json
import os
import re
import time
from typing import Any

from ..config import HarnessConfig
from ..legacy_runner import run_harness


class GSM8KAdapter:
    def __init__(
        self,
        suite_path: str,
        provider: str = "stub",
        model: str = "",
        base_url: str = "",
        allow_stub: bool = True,
    ):
        self.suite_path = suite_path
        self.provider = provider
        self.model = model
        self.base_url = base_url
        self.allow_stub = allow_stub
        self.results: list[dict[str, Any]] = []

    def load_suite(self) -> list[dict[str, Any]]:
        if not os.path.exists(self.suite_path):
            raise FileNotFoundError(f"GSM8K suite file not found: {self.suite_path}")
        with open(self.suite_path) as f:
            return json.load(f)

    @staticmethod
    def extract_answer(text: str) -> str | None:
        match = re.search(r"####\s*(-?\d+(?:\.\d+)?)", text)
        if match:
            return match.group(1).strip()
        match = re.search(r"\*\*Answer:\*\*\s*(-?\d+(?:\.\d+)?)", text)
        if match:
            return match.group(1).strip()
        match = re.search(r"answer\s*is\s*(-?\d+(?:\.\d+)?)", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    @staticmethod
    def extract_predicted(text: str, events: list[dict[str, Any]] | None = None) -> str | None:
        candidates = []

        sources = []
        if events:
            for ev in events:
                msg = ev.get("message", "")
                actions = {"final", "result"}
                if msg and ev.get("action_type", "") in actions:
                    sources.append(msg)

        if text:
            sources.append(text)

        for source in sources:
            text_clean = source.replace(",", "")
            patterns = [
                r"(?:answer|result|value|number|total)\s*(?:is|:|=|was)\s*(-?\d+(?:\.\d+)?)",
                r"(?:therefore|so|thus)\s+(?:the\s+)?(?:answer|result|value)\s+(?:is|:|=)\s*(-?\d+(?:\.\d+)?)",
                r"\*\*(-?\d+(?:\.\d+)?)\*\*",
            ]
            for pat in patterns:
                match = re.search(pat, text_clean, re.IGNORECASE | re.MULTILINE)
                if match:
                    candidates.append(match.group(1))

            numbers = re.findall(r"-?\d+(?:\.\d+)?", text_clean)
            if numbers:
                candidates.append(numbers[-1])

        for candidate in candidates:
            try:
                float(candidate.replace(",", ""))
                return candidate
            except ValueError:
                continue

        return None

    @staticmethod
    def normalize_number(s: str) -> float | None:
        s = s.strip().replace(",", "")
        try:
            return float(s)
        except ValueError:
            return None

    async def run_task(self, task: dict[str, Any]) -> dict[str, Any]:
        task_id = task.get("task_id", "unknown")
        question = task.get("question", "")
        answer_text = task.get("answer", "")
        expected = self.extract_answer(answer_text)

        events: list[dict[str, Any]] = []
        def collect_events(event: dict[str, Any]):
            events.append(event)

        start = time.perf_counter()
        res = await run_harness(
            task=question,
            allow_stub=self.allow_stub,
            config=HarnessConfig(
                code_agent="benchmark-agent",
                provider=self.provider,
                model=self.model,
                base_url=self.base_url,
                max_steps=5,
            ),
            progress_callback=collect_events,
        )
        duration_ms = int((time.perf_counter() - start) * 1000)

        predicted = None
        predicted = self.extract_predicted(res.message or "", events)
        if predicted is None and res.events:
            predicted = self.extract_predicted("", res.events)

        correct = False
        if expected is not None and predicted is not None:
            e_norm = self.normalize_number(expected)
            p_norm = self.normalize_number(predicted)
            if e_norm is not None and p_norm is not None:
                correct = abs(e_norm - p_norm) < 0.01

        return {
            "task_id": task_id,
            "success": correct,
            "expected": expected,
            "predicted": predicted,
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
            print(f"Running GSM8K task: {task.get('task_id', 'unknown')}")
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
            "type": "gsm8k",
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
