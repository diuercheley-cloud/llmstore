from typing import Any

from pydantic import BaseModel, Field


class EvalCase(BaseModel):
    id: str
    task: str
    input_files: dict[str, str] | None = None
    expected_files: dict[str, str] | None = None
    test_command: str | None = None
    expected_stdout: str | None = None
    expected_status: int | None = None
    timeout_seconds: int | None = None
    tags: list[str] | None = None


class EvalSuite(BaseModel):
    name: str
    description: str | None = None
    cases: list[EvalCase]


class JudgeVerdictModel(BaseModel):
    score: float = 0.0
    passed: bool = False
    reason: str = ""
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    risk_level: str = "medium"


class CaseScore(BaseModel):
    case_id: str
    passed: bool
    checks: dict[str, bool] = Field(default_factory=dict)
    details: dict[str, Any] = Field(default_factory=dict)
    duration_seconds: float = 0.0
    error: str | None = None
    judge_verdict: JudgeVerdictModel | None = None


class EvalResult(BaseModel):
    suite_name: str
    total_cases: int
    passed: int
    failed: int
    accuracy: float
    pass_at_1: float
    total_duration_seconds: float
    case_scores: list[CaseScore] = Field(default_factory=list)
    total_tokens: int = 0
    estimated_cost: float = 0.0


class EvalReport(BaseModel):
    suite_name: str
    description: str | None = None
    total_cases: int
    passed: int
    failed: int
    accuracy: float
    pass_at_1: float
    total_duration_seconds: float
    case_results: list[dict[str, Any]] = Field(default_factory=list)
