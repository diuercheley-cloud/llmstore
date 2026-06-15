# Owner: agent-platform
import asyncio
import logging
import uuid

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.agents.agent_optimization import (
    AgentOptimizationCandidate,
    AgentPolicyCandidate,
    AgentPromptCandidate,
    AgentToolSelectionCandidate,
)
from app.models.agents.agent_optimization_tournament import (
    AgentOptimizationTournament,
    AgentOptimizationTournamentCandidate,
    AgentOptimizationTournamentResult,
)
from app.models.agents.agents import AgentDefinition, AgentEvalRun, AgentEvalSuite
from app.services.agents.agent_evals import AgentEvalService
from app.services.agents.optimization.ab_testing import ABTestingService
from app.services.agents.optimization.candidate_ranker import CandidateRanker
from app.services.agents.optimization.statistical_scoring import StatisticalScoringService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class TournamentRunner:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.eval_service = AgentEvalService(db)
        self.scoring = StatisticalScoringService()
        self.ab_testing = ABTestingService()
        self.ranker = CandidateRanker(self.scoring)

    async def create_tournament(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
        candidate_ids: list[uuid.UUID],
        parallel_limit: int = 2,
    ) -> AgentOptimizationTournament:
        settings = get_settings()
        if not settings.agent_optimizer_tournaments_enabled:
            raise PermissionError("Tournament evaluation is disabled by feature flag.")

        stmt = select(AgentDefinition).where(AgentDefinition.id == agent_id)
        res_agent = await self.db.execute(stmt)
        agent = res_agent.scalar_one_or_none()
        if not agent:
            raise ValueError(f"Agent {agent_id} not found.")

        tournament = AgentOptimizationTournament(
            tenant_id=tenant_id,
            agent_id=agent_id,
            status="draft",
            candidate_ids=[str(cid) for cid in candidate_ids],
            parallel_limit=parallel_limit,
        )
        self.db.add(tournament)
        await self.db.flush()

        for idx, cid in enumerate(candidate_ids):
            stmt = select(AgentOptimizationCandidate).where(AgentOptimizationCandidate.id == cid)
            res_cand = await self.db.execute(stmt)
            candidate = res_cand.scalar_one_or_none()
            if not candidate:
                raise ValueError(f"Candidate {cid} not found.")
            t_candidate = AgentOptimizationTournamentCandidate(
                tournament_id=tournament.id,
                candidate_id=cid,
                tenant_id=tenant_id,
                agent_id=agent_id,
                label=candidate.candidate_type if candidate.candidate_type else f"candidate-{idx}",
                status="pending",
            )
            self.db.add(t_candidate)

        await self.db.flush()
        return tournament

    async def run_tournament(
        self,
        tournament_id: uuid.UUID,
    ) -> AgentOptimizationTournament:
        settings = get_settings()
        if not settings.agent_optimizer_tournaments_enabled:
            raise PermissionError("Tournament evaluation is disabled by feature flag.")

        stmt = select(AgentOptimizationTournament).where(
            AgentOptimizationTournament.id == tournament_id
        )
        res_t = await self.db.execute(stmt)
        tournament = res_t.scalar_one_or_none()
        if not tournament:
            raise ValueError(f"Tournament {tournament_id} not found.")

        if tournament.status not in ("draft", "failed"):
            raise ValueError(
                f"Tournament is already {tournament.status}. "
                "Only draft or failed tournaments can be run."
            )

        tournament.status = "running"
        await self.db.flush()

        try:
            await self._evaluate_all_candidates(tournament)
            await self._compute_results(tournament)
            tournament.status = "completed"
        except Exception:
            tournament.status = "failed"
            logger.exception(f"Tournament {tournament_id} failed.")
            await self.db.flush()
            raise

        await self.db.flush()
        return tournament

    async def _evaluate_all_candidates(
        self, tournament: AgentOptimizationTournament
    ) -> dict[uuid.UUID, dict]:
        stmt = select(AgentOptimizationTournamentCandidate).where(
            AgentOptimizationTournamentCandidate.tournament_id == tournament.id
        )
        res_tc = await self.db.execute(stmt)
        t_candidates = list(res_tc.scalars().all())

        parallel = bool(get_settings().agent_optimizer_parallel_evals_enabled)
        limit = tournament.parallel_limit if parallel else 1

        metrics_map: dict[uuid.UUID, dict] = {}
        semaphore = asyncio.Semaphore(limit)

        async def _eval_one(
            tc: AgentOptimizationTournamentCandidate,
        ) -> tuple[uuid.UUID, dict]:
            async with semaphore:
                metrics = await self._evaluate_single_candidate(tc, tournament)
                return tc.id, metrics

        tasks = [_eval_one(tc) for tc in t_candidates]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for r in results:
            if isinstance(r, Exception):
                logger.error(f"Tournament eval failed: {r}")
                continue
            tc_id, metrics = r
            metrics_map[tc_id] = metrics

        return metrics_map

    async def _evaluate_single_candidate(
        self,
        tc: AgentOptimizationTournamentCandidate,
        tournament: AgentOptimizationTournament,
    ) -> dict:
        tc.status = "evaluating"
        await self.db.flush()

        suite = await self._ensure_eval_suite(tournament.agent_id)
        candidate_run = await self.eval_service.run_eval_suite(
            suite.id,
            metadata={
                "candidate_id": str(tc.candidate_id),
                "tournament_id": str(tournament.id),
            },
        )
        await self.db.flush()

        stmt_base = (
            select(AgentEvalRun)
            .where(
                AgentEvalRun.suite_id == suite.id,
                AgentEvalRun.status == "completed",
            )
            .order_by(AgentEvalRun.completed_at.desc())
        )
        res_base = await self.db.execute(stmt_base)
        baseline_run = res_base.scalar_one_or_none()

        if not baseline_run:
            baseline_run = await self.eval_service.run_eval_suite(
                suite.id, metadata={"context": "baseline"}
            )
            await self.db.flush()

        total = candidate_run.total_count or 1
        cand_pass_rate = candidate_run.passed_count / total

        success_rate = cand_pass_rate
        run_metrics = getattr(candidate_run, "metrics", None) or {}

        latency_p50 = float(run_metrics.get("latency_p50", 0))
        latency_p95 = float(run_metrics.get("latency_p95", 0))
        cost = float(run_metrics.get("cost", 0))
        tool_error_rate = candidate_run.failed_count / total

        policy_denial_rate = 0.0
        safety_failure_rate = 0.0

        stmt_cand = select(AgentOptimizationCandidate).where(
            AgentOptimizationCandidate.id == tc.candidate_id
        )
        res_cand = await self.db.execute(stmt_cand)
        candidate = res_cand.scalar_one_or_none()
        if candidate and candidate.safety_regression:
            safety_failure_rate = 1.0

        tc.status = "completed"
        tc.eval_run_id = candidate_run.id

        metrics = {
            "success_rate": round(success_rate, 4),
            "latency_p50": round(latency_p50, 2),
            "latency_p95": round(latency_p95, 2),
            "cost": round(cost, 6),
            "tool_error_rate": round(tool_error_rate, 4),
            "policy_denial_rate": round(policy_denial_rate, 4),
            "safety_failure_rate": round(safety_failure_rate, 4),
        }
        await self.db.flush()
        return metrics

    async def _ensure_eval_suite(self, agent_id: uuid.UUID) -> AgentEvalSuite:
        stmt = select(AgentEvalSuite).where(AgentEvalSuite.agent_id == agent_id)
        res = await self.db.execute(stmt)
        suite = res.scalar_one_or_none()
        if not suite:
            suite = await self.eval_service.create_suite(
                agent_id, "Tournament Suite", "Created for tournament evaluation"
            )
            await self.eval_service.create_case(
                suite.id,
                {
                    "name": "Standard Check",
                    "input_text": "Verify system bounds",
                    "assertions": [{"type": "final_answer_contains", "value": "system"}],
                },
            )
            await self.db.flush()
        return suite

    async def _compute_results(self, tournament: AgentOptimizationTournament) -> None:
        stmt = select(AgentOptimizationTournamentCandidate).where(
            AgentOptimizationTournamentCandidate.tournament_id == tournament.id
        )
        res_tc = await self.db.execute(stmt)
        t_candidates = list(res_tc.scalars().all())

        baseline_metrics = await self._compute_baseline_metrics(tournament.agent_id)

        metrics_map: dict[uuid.UUID, dict] = {}
        for tc in t_candidates:
            raw_metrics = {
                "success_rate": 0.0,
                "latency_p50": 0.0,
                "latency_p95": 0.0,
                "cost": 0.0,
                "tool_error_rate": 0.0,
                "policy_denial_rate": 0.0,
                "safety_failure_rate": 0.0,
            }
            stmt_r = select(AgentOptimizationTournamentResult).where(
                AgentOptimizationTournamentResult.tournament_candidate_id == tc.id
            )
            res_r = await self.db.execute(stmt_r)
            existing_result = res_r.scalar_one_or_none()
            if existing_result:
                raw_metrics = existing_result.metrics
            metrics_map[tc.id] = raw_metrics

        results = self.ranker.rank_candidates(
            tournament, t_candidates, metrics_map, baseline_metrics
        )
        for r in results:
            stmt_ex = select(AgentOptimizationTournamentResult).where(
                AgentOptimizationTournamentResult.tournament_candidate_id
                == r.tournament_candidate_id
            )
            existing = await self.db.execute(stmt_ex)
            old = existing.scalar_one_or_none()
            if old:
                old.score = r.score
                old.rank = r.rank
                old.safety_regression = r.safety_regression
                old.metrics = r.metrics
            else:
                self.db.add(r)

        pairwise = self.ab_testing.build_pairwise_results(tournament, t_candidates, metrics_map)
        for p in pairwise:
            self.db.add(p)

        winner = self.ranker.select_winner(results)
        if winner:
            tournament.winner_id = winner.tournament_candidate_id

        all_scores = [r.score for r in results if r.score is not None]
        tournament.confidence_score = self.scoring.compute_confidence_score(
            all_scores,
            winner.score if winner else 0.0,
        )

        tournament.ranking = self.ranker.build_ranking_list(results)
        tournament.rollback_point = await self._capture_rollback_point(tournament.agent_id)

        await self.db.flush()

    async def _compute_baseline_metrics(self, agent_id: uuid.UUID) -> dict:
        stmt = select(AgentEvalSuite).where(AgentEvalSuite.agent_id == agent_id)
        res = await self.db.execute(stmt)
        suite = res.scalar_one_or_none()
        if not suite:
            return {}

        stmt_run = (
            select(AgentEvalRun)
            .where(
                AgentEvalRun.suite_id == suite.id,
                AgentEvalRun.status == "completed",
            )
            .order_by(AgentEvalRun.completed_at.desc())
        )
        res_run = await self.db.execute(stmt_run)
        baseline_run = res_run.scalar_one_or_none()
        if not baseline_run:
            return {}

        total = baseline_run.total_count or 1
        base_pass_rate = baseline_run.passed_count / total
        run_metrics = getattr(baseline_run, "metrics", None) or {}

        return {
            "success_rate": base_pass_rate,
            "latency_p50": float(run_metrics.get("latency_p50", 0)),
            "latency_p95": float(run_metrics.get("latency_p95", 0)),
            "cost": float(run_metrics.get("cost", 0)),
            "tool_error_rate": 0.0,
            "policy_denial_rate": 0.0,
            "safety_failure_rate": 0.0,
        }

    async def _capture_rollback_point(self, agent_id: uuid.UUID) -> dict:
        stmt = select(AgentDefinition).where(AgentDefinition.id == agent_id)
        res = await self.db.execute(stmt)
        agent = res.scalar_one_or_none()
        if not agent:
            return {}
        return {
            "agent_id": str(agent.id),
            "instructions": agent.instructions,
            "allowed_tools": agent.allowed_tools or [],
            "policy_id": agent.policy_id,
            "captured_at": utc_now().isoformat(),
        }

    async def approve_winner(self, tournament_id: uuid.UUID) -> AgentOptimizationTournament:
        settings = get_settings()
        if not settings.agent_optimizer_tournaments_enabled:
            raise PermissionError("Tournament evaluation is disabled by feature flag.")

        stmt = select(AgentOptimizationTournament).where(
            AgentOptimizationTournament.id == tournament_id
        )
        res_t = await self.db.execute(stmt)
        tournament = res_t.scalar_one_or_none()
        if not tournament:
            raise ValueError(f"Tournament {tournament_id} not found.")
        if tournament.status != "completed":
            raise ValueError(
                "Tournament must be completed before approving winner. "
                f"Current status: {tournament.status}"
            )
        if not tournament.winner_id:
            raise ValueError("No winner to approve. Run the tournament first.")

        tournament.approval_status = "approved"
        tournament.approved_at = utc_now()
        await self.db.flush()
        return tournament

    async def apply_winner(self, tournament_id: uuid.UUID) -> AgentOptimizationTournament:
        settings = get_settings()
        if not settings.agent_optimizer_tournaments_enabled:
            raise PermissionError("Tournament evaluation is disabled by feature flag.")
        if not settings.agent_optimizer_apply_winner_enabled:
            raise PermissionError("Applying tournament winner is disabled by feature flag.")

        stmt = select(AgentOptimizationTournament).where(
            AgentOptimizationTournament.id == tournament_id
        )
        res_t = await self.db.execute(stmt)
        tournament = res_t.scalar_one_or_none()
        if not tournament:
            raise ValueError(f"Tournament {tournament_id} not found.")
        if tournament.approval_status != "approved":
            raise PermissionError("Winner must be approved before applying.")
        if not tournament.winner_id:
            raise ValueError("No winner selected.")

        stmt_w = select(AgentOptimizationTournamentCandidate).where(
            AgentOptimizationTournamentCandidate.id == tournament.winner_id
        )
        res_tc = await self.db.execute(stmt_w)
        t_winner = res_tc.scalar_one_or_none()
        if not t_winner:
            raise ValueError(f"Winner candidate {tournament.winner_id} not found.")

        stmt_c = select(AgentOptimizationCandidate).where(
            AgentOptimizationCandidate.id == t_winner.candidate_id
        )
        res_cand = await self.db.execute(stmt_c)
        candidate = res_cand.scalar_one_or_none()
        if not candidate:
            raise ValueError(f"Candidate {t_winner.candidate_id} not found.")

        stmt_a = select(AgentDefinition).where(AgentDefinition.id == tournament.agent_id)
        res_agent = await self.db.execute(stmt_a)
        agent = res_agent.scalar_one_or_none()
        if not agent:
            raise ValueError(f"Agent {tournament.agent_id} not found.")

        if candidate.candidate_type == "prompt":
            stmt_pd = select(AgentPromptCandidate).where(
                AgentPromptCandidate.candidate_id == candidate.id
            )
            res_pd = await self.db.execute(stmt_pd)
            pd = res_pd.scalar_one_or_none()
            if pd:
                agent.instructions = pd.prompt_text
        elif candidate.candidate_type == "tool_selection":
            stmt_td = select(AgentToolSelectionCandidate).where(
                AgentToolSelectionCandidate.candidate_id == candidate.id
            )
            res_td = await self.db.execute(stmt_td)
            td = res_td.scalar_one_or_none()
            if td:
                agent.allowed_tools = td.allowed_tools
        elif candidate.candidate_type == "policy":
            stmt_pol = select(AgentPolicyCandidate).where(
                AgentPolicyCandidate.candidate_id == candidate.id
            )
            res_pol = await self.db.execute(stmt_pol)
            pol = res_pol.scalar_one_or_none()
            if pol:
                agent.policy_id = f"policy-tournament-{candidate.id}"

        candidate.status = "applied"
        tournament.applied_at = utc_now()
        agent.updated_at = utc_now()
        await self.db.flush()
        return tournament
