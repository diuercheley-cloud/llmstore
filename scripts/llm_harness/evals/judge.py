import abc
import json
import logging
import os
from enum import Enum
from typing import Any

import httpx

from ..sanitizer import Sanitizer

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class JudgeVerdict:
    def __init__(
        self,
        score: float = 0.0,
        passed: bool = False,
        reason: str = "",
        strengths: list[str] | None = None,
        weaknesses: list[str] | None = None,
        risk_level: str = "medium",
    ):
        self.score = max(0.0, min(1.0, score))
        self.passed = passed
        self.reason = reason
        self.strengths = strengths or []
        self.weaknesses = weaknesses or []
        self.risk_level = risk_level

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JudgeVerdict":
        return cls(
            score=float(data.get("score", 0.0)),
            passed=bool(data.get("passed", False)),
            reason=str(data.get("reason", "")),
            strengths=list(data.get("strengths", [])),
            weaknesses=list(data.get("weaknesses", [])),
            risk_level=str(data.get("risk_level", "medium")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "passed": self.passed,
            "reason": Sanitizer.sanitize_text(self.reason),
            "strengths": [Sanitizer.sanitize_text(s) for s in self.strengths],
            "weaknesses": [Sanitizer.sanitize_text(w) for w in self.weaknesses],
            "risk_level": self.risk_level,
        }


JUDGE_SYSTEM_PROMPT = (
    "You are an expert code review judge. "
    "Evaluate the quality of the solution provided for the given coding task.\n\n"
    "Evaluate based on:\n"
    "1. Correctness - Does the solution correctly solve the task?\n"
    "2. Code quality - Is the code well-structured, readable, and idiomatic?\n"
    "3. Completeness - Are all requirements addressed?\n"
    "4. Test quality - Are tests passing and well-written?\n\n"
    'Return a JSON object with these fields:\n'
    '{\n'
    '  "score": 0.0 to 1.0,\n'
    '  "passed": true/false,\n'
    '  "reason": "Detailed explanation of the evaluation",\n'
    '  "strengths": ["list of strengths"],\n'
    '  "weaknesses": ["list of weaknesses"],\n'
    '  "risk_level": "low|medium|high"\n'
    '}\n\n'
    "Be objective and thorough. Score below 0.7 means the solution has significant issues."
)


class BaseJudgeProvider(abc.ABC):
    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.model = config.get("model", "")
        self.base_url = (config.get("base_url") or "").rstrip("/")
        self.api_key_env = config.get("api_key_env", "OPENAI_API_KEY")
        self.timeout = config.get("timeout", 30.0)
        self.max_retries = max(0, config.get("max_retries", 3))
        self.threshold = max(0.0, min(1.0, config.get("threshold", 0.75)))

    @abc.abstractmethod
    async def judge(
        self,
        task: str,
        diff: str = "",
        test_output: str = "",
        harness_report: str = "",
        criteria: dict[str, Any] | None = None,
    ) -> JudgeVerdict:
        pass

    def _get_api_key(self) -> str:
        return os.getenv(self.api_key_env, "")

    def _build_judge_messages(
        self,
        task: str,
        diff: str,
        test_output: str,
        harness_report: str,
        criteria: dict[str, Any] | None,
    ) -> list[dict[str, str]]:
        criteria_str = ""
        if criteria:
            criteria_str = "\n## Evaluation Criteria\n" + json.dumps(criteria, indent=2)

        user_content = (
            f"## Task\n{task}\n\n"
            f"## Changes (Diff)\n```\n{diff or '(no diff provided)'}\n```\n\n"
            f"## Test Output\n```\n{test_output or '(no test output)'}\n```\n\n"
            f"## Execution Report\n```\n{harness_report or '(no report)'}\n```\n"
            f"{criteria_str}"
        )

        return [
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]


class DisabledJudgeProvider(BaseJudgeProvider):
    async def judge(
        self,
        task: str = "",
        diff: str = "",
        test_output: str = "",
        harness_report: str = "",
        criteria: dict[str, Any] | None = None,
    ) -> JudgeVerdict:
        return JudgeVerdict(score=0.0, passed=True, reason="Judge disabled")


class OpenAICompatibleJudgeProvider(BaseJudgeProvider):
    def _validate_config(self):
        if not self.base_url:
            raise ValueError("base_url is required for judge provider")
        if not self.model:
            raise ValueError("model is required for judge provider")
        if not self._get_api_key():
            raise ValueError(
                f"API key not found in environment variable {self.api_key_env}"
            )

    def _build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        api_key = self._get_api_key()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    async def _request(self, payload: dict[str, Any]) -> dict[str, Any]:
        from ..utils.retry import async_retry

        base = self.base_url.rstrip("/")
        url = f"{base}/v1/chat/completions"
        if not url.startswith("http"):
            url = f"https://{url}"

        async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout)) as client:
            async def _do_post() -> dict[str, Any]:
                response = await client.post(
                    url, json=payload, headers=self._build_headers()
                )
                response.raise_for_status()
                return response.json()

            return await async_retry(
                _do_post,
                max_retries=self.max_retries,
                base_delay=1.0,
                retryable_errors=(
                    httpx.TimeoutException,
                    httpx.NetworkError,
                    httpx.HTTPStatusError,
                ),
            )

    async def judge(
        self,
        task: str = "",
        diff: str = "",
        test_output: str = "",
        harness_report: str = "",
        criteria: dict[str, Any] | None = None,
    ) -> JudgeVerdict:
        self._validate_config()
        messages = self._build_judge_messages(task, diff, test_output, harness_report, criteria)

        payload = {
            "model": self.model,
            "messages": messages,
            "response_format": {"type": "json_object"},
        }

        try:
            data = await self._request(payload)
            content = ""
            if isinstance(data.get("choices"), list) and len(data["choices"]) > 0:
                content = str(data["choices"][0].get("message", {}).get("content", ""))

            if not content:
                logger.warning("Judge returned empty content, returning default verdict")
                return JudgeVerdict(score=0.0, passed=False, reason="Judge returned empty response")

            cleaned = content.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
                end_idx = cleaned.rfind("```")
                if end_idx >= 0:
                    cleaned = cleaned[:end_idx]
                cleaned = cleaned.strip()

            verdict_data = json.loads(cleaned)
            verdict = JudgeVerdict.from_dict(verdict_data)
            return verdict

        except Exception as exc:
            logger.error("Judge evaluation failed: %s", exc)
            return JudgeVerdict(score=0.0, passed=False, reason=f"Judge error: {exc}")


class LocalOpenAICompatibleJudgeProvider(OpenAICompatibleJudgeProvider):
    def _validate_config(self):
        if not self.base_url:
            raise ValueError("base_url is required for judge provider")
        if not self.model:
            raise ValueError("model is required for judge provider")


_JUDGE_REGISTRY: dict[str, type[BaseJudgeProvider]] = {}


def register_judge(name: str, cls: type[BaseJudgeProvider]):
    _JUDGE_REGISTRY[name] = cls


def create_judge(name: str, config: dict[str, Any]) -> BaseJudgeProvider:
    if name not in _JUDGE_REGISTRY:
        raise ValueError(f"Unknown judge provider: {name}")
    return _JUDGE_REGISTRY[name](config)


register_judge("disabled", DisabledJudgeProvider)
register_judge("openai-compatible", OpenAICompatibleJudgeProvider)
register_judge("local-openai-compatible", LocalOpenAICompatibleJudgeProvider)


def build_judge_config_from_args(args) -> dict[str, Any]:
    judge_name = getattr(args, "judge", None) or "disabled"
    return {
        "provider": judge_name,
        "model": getattr(args, "judge_model", None) or "",
        "base_url": getattr(args, "judge_base_url", None) or "",
        "api_key_env": getattr(args, "judge_api_key_env", None) or "OPENAI_API_KEY",
        "threshold": float(getattr(args, "judge_threshold", 0.75)),
    }
