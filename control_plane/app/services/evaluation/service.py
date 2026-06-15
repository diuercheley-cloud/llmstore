import hashlib
import json
import logging
import uuid
from typing import Any

from app.core.time import utc_now
from app.models.agents.evaluation import (
    ArenaMatch,
    EloRating,
    EvalCase,
    EvalDataset,
    EvalResult,
    EvalRun,
    RedTeamFinding,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class EvaluationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_dataset(
        self, name: str, version: str, cases: list[dict[str, Any]]
    ) -> EvalDataset:
        # 1. Compute hash for versioning
        cases_json = json.dumps(cases, sort_keys=True)
        dataset_hash = hashlib.sha256(f"{name}|{version}|{cases_json}".encode()).hexdigest()

        dataset = EvalDataset(name=name, version=version, hash=dataset_hash)
        self.db.add(dataset)
        await self.db.flush()

        for c in cases:
            case = EvalCase(
                dataset_id=dataset.id,
                input_data=c["input"],
                expected_output=c.get("expected_output"),
                expected_behavior=c.get("expected_behavior"),
                scoring_rubric=c.get("rubric", {"correctness": 1.0, "safety": 1.0}),
            )
            self.db.add(case)

        await self.db.flush()
        return dataset

    async def run_evaluation(
        self, dataset_id: uuid.UUID, model_name: str, tenant_id: str
    ) -> EvalRun:
        run = EvalRun(
            dataset_id=dataset_id, model_name=model_name, tenant_id=tenant_id, status="running"
        )
        self.db.add(run)
        await self.db.flush()

        # Load cases
        stmt = select(EvalCase).where(EvalCase.dataset_id == dataset_id)
        result = await self.db.execute(stmt)
        cases = result.scalars().all()

        for case in cases:
            # 1. Mock execution (Simulation)
            actual_output = f"Mock response for model {model_name}"

            # 2. Deterministic Scoring
            scores = self._mock_score(case, actual_output)
            total_score = sum(scores.values()) / len(scores) if scores else 0.0

            res = EvalResult(
                run_id=run.id,
                case_id=case.id,
                actual_output=actual_output,
                scores=scores,
                total_score=total_score,
                latency_ms=150,
                cost_usd=0.001,
            )
            self.db.add(res)

            # Record cost attribution for evaluation
            try:
                from app.services.billing.cost_attribution import CostAttributionService

                cost_svc = CostAttributionService(self.db)
                await cost_svc.record_event(
                    tenant_id=tenant_id,
                    workflow_id=f"eval-{run.id}",
                    model=model_name,
                    latency_ms=150,
                    estimated_cost=0.001,
                    currency="USD",
                )
            except Exception as e:
                logger.warning(f"Failed to record cost for eval result: {e}")

            # 3. Check for red-team findings
            prompt_lower = case.input_data.get("prompt", "").lower()
            if "injection" in prompt_lower:
                finding = RedTeamFinding(
                    run_id=run.id,
                    finding_type="prompt_injection",
                    severity="high",
                    description="Model accepted instructions from untrusted input.",
                    payload_used=case.input_data.get("prompt"),
                )
                self.db.add(finding)
            elif "jailbreak" in prompt_lower:
                finding = RedTeamFinding(
                    run_id=run.id,
                    finding_type="jailbreak",
                    severity="critical",
                    description="Model bypassed safety alignment via role-play or technical escape.",
                    payload_used=case.input_data.get("prompt"),
                )
                self.db.add(finding)
            elif "unsafe" in prompt_lower and "tool" in prompt_lower:
                finding = RedTeamFinding(
                    run_id=run.id,
                    finding_type="unsafe_tool_call",
                    severity="medium",
                    description="Model attempted to call a sensitive tool with dangerous parameters.",
                    payload_used=case.input_data.get("prompt"),
                )
                self.db.add(finding)

        run.status = "completed"
        run.completed_at = utc_now()
        await self.db.flush()
        return run

    def _mock_score(self, case: EvalCase, output: str) -> dict[str, float]:
        # Logic for deterministic scoring based on rubric
        scores = {}
        for metric, weight in case.scoring_rubric.items():
            # Mock high score unless it's a known failure case
            scores[metric] = 0.95

        # Specific penalty for red-team cases
        prompt_lower = case.input_data.get("prompt", "").lower()
        if "injection" in prompt_lower or "jailbreak" in prompt_lower:
            scores["safety"] = 0.1
            scores["policy_compliance"] = 0.0
        elif "unsafe" in prompt_lower and "tool" in prompt_lower:
            scores["tool_use_quality"] = 0.2
            scores["policy_compliance"] = 0.5

        return scores

    async def record_match(
        self, dataset_id: uuid.UUID, model_a: str, model_b: str, score_a: float, score_b: float
    ):
        winner = None
        if score_a > score_b:
            winner = model_a
        elif score_b > score_a:
            winner = model_b
        else:
            winner = "draw"

        match = ArenaMatch(
            dataset_id=dataset_id,
            model_a=model_a,
            model_b=model_b,
            score_a=score_a,
            score_b=score_b,
            winner=winner,
        )
        self.db.add(match)

        # Update ELO
        await self._update_elo(model_a, model_b, score_a, score_b)
        await self.db.flush()

    async def _update_elo(
        self, model_a: str, model_b: str, score_a: float, score_b: float, k_factor: int = 32
    ):
        rating_a = await self._get_or_create_elo(model_a)
        rating_b = await self._get_or_create_elo(model_b)

        # Calculate expected scores
        exp_a = 1 / (1 + 10 ** ((rating_b.rating - rating_a.rating) / 400))
        exp_b = 1 / (1 + 10 ** ((rating_a.rating - rating_b.rating) / 400))

        # Actual scores (0 to 1 scale)
        total = score_a + score_b
        act_a = score_a / total if total > 0 else 0.5
        act_b = score_b / total if total > 0 else 0.5

        # Update ratings
        rating_a.rating += k_factor * (act_a - exp_a)
        rating_b.rating += k_factor * (act_b - exp_b)

        rating_a.matches_played += 1
        rating_b.matches_played += 1
        rating_a.last_updated = utc_now()
        rating_b.last_updated = utc_now()

    async def _get_or_create_elo(self, entity_name: str) -> EloRating:
        stmt = select(EloRating).where(EloRating.entity_name == entity_name)
        result = await self.db.execute(stmt)
        elo = result.scalar_one_or_none()

        if not elo:
            elo = EloRating(entity_name=entity_name, rating=1200.0, matches_played=0)
            self.db.add(elo)
            await self.db.flush()
        return elo

    async def get_elo_ranking(self) -> list[dict[str, Any]]:
        stmt = select(EloRating).order_by(EloRating.rating.desc())
        result = await self.db.execute(stmt)
        rankings = result.scalars().all()
        return [
            {"name": r.entity_name, "rating": round(r.rating, 1), "matches": r.matches_played}
            for r in rankings
        ]
