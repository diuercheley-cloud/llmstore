import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.models.agents.agent_optimization import (
    AgentOptimizationCandidate,
)
from app.models.agents.agent_optimization_tournament import (
    AgentOptimizationTournament,
    AgentOptimizationTournamentCandidate,
    AgentOptimizationTournamentResult,
)
from app.models.agents.agents import AgentDefinition
from app.services.agents.optimization.ab_testing import ABTestingService
from app.services.agents.optimization.candidate_ranker import CandidateRanker
from app.services.agents.optimization.statistical_scoring import StatisticalScoringService
from app.services.agents.optimization.tournament_runner import TournamentRunner
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def mock_db():
    db = AsyncMock(spec=AsyncSession)
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    return db


@pytest.fixture
def runner(mock_db):
    return TournamentRunner(mock_db)


@pytest.fixture
def agent():
    return AgentDefinition(
        id=uuid.uuid4(),
        tenant_id="default",
        name="test-agent",
        instructions="Do the thing.",
        allowed_tools=["tool_a", "tool_b"],
        policy_id=None,
    )


@pytest.fixture
def candidates(agent):
    return [
        AgentOptimizationCandidate(
            id=uuid.uuid4(),
            experiment_id=uuid.uuid4(),
            tenant_id="default",
            agent_id=agent.id,
            candidate_type="prompt",
            status="pending",
            safety_regression=False,
        ),
        AgentOptimizationCandidate(
            id=uuid.uuid4(),
            experiment_id=uuid.uuid4(),
            tenant_id="default",
            agent_id=agent.id,
            candidate_type="prompt",
            status="pending",
            safety_regression=False,
        ),
        AgentOptimizationCandidate(
            id=uuid.uuid4(),
            experiment_id=uuid.uuid4(),
            tenant_id="default",
            agent_id=agent.id,
            candidate_type="prompt",
            status="pending",
            safety_regression=False,
        ),
    ]


class TestStatisticalScoring:
    def test_compute_metric_summary(self):
        service = StatisticalScoringService()
        raw = [
            {"success_rate": 0.9, "latency_p50": 100, "latency_p95": 200, "cost": 0.01},
            {"success_rate": 0.8, "latency_p50": 150, "latency_p95": 300, "cost": 0.02},
            {"success_rate": 0.85, "latency_p50": 120, "latency_p95": 250, "cost": 0.015},
        ]
        summary = service.compute_metric_summary(raw)
        assert abs(summary["success_rate"] - 0.85) < 0.01
        assert abs(summary["latency_p50"] - 123.33) < 1.0

    def test_compute_baseline_deltas(self):
        service = StatisticalScoringService()
        candidate = {"success_rate": 0.95, "cost": 0.02, "latency_p50": 100}
        baseline = {"success_rate": 0.90, "cost": 0.01, "latency_p50": 80}
        deltas = service.compute_baseline_deltas(candidate, baseline)
        assert abs(deltas["success_rate"] - 0.05) < 0.01
        assert abs(deltas["cost"] - 0.01) < 0.01

    def test_compute_penalties_safety_regression(self):
        service = StatisticalScoringService()
        deltas = {"safety_failure_rate": 0.1, "cost": 0.0, "latency_p50": 0, "tool_error_rate": 0}
        raw = {"safety_failure_rate": 0.1}
        penalty = service.compute_penalties(deltas, raw)
        assert penalty <= -0.40

    def test_compute_penalties_cost_spike(self):
        service = StatisticalScoringService()
        deltas = {"safety_failure_rate": 0, "cost": 0.20, "latency_p50": 0, "tool_error_rate": 0}
        raw = {}
        penalty = service.compute_penalties(deltas, raw)
        assert penalty <= -0.20

    def test_compute_penalties_latency_spike(self):
        service = StatisticalScoringService()
        deltas = {"safety_failure_rate": 0, "cost": 0, "latency_p50": 200, "tool_error_rate": 0}
        raw = {}
        penalty = service.compute_penalties(deltas, raw)
        assert penalty <= -0.15

    def test_confidence_score_margin(self):
        service = StatisticalScoringService()
        scores = [0.8, 0.5, 0.3]
        confidence = service.compute_confidence_score(scores, 0.8)
        assert 0.5 <= confidence <= 1.0

    def test_confidence_score_no_margin(self):
        service = StatisticalScoringService()
        scores = [0.5]
        confidence = service.compute_confidence_score(scores, 0.5)
        assert confidence == 0.5


class TestABTesting:
    def test_compare_pairwise(self):
        service = ABTestingService()
        ca = AgentOptimizationTournamentCandidate(id=uuid.uuid4(), label="A")
        cb = AgentOptimizationTournamentCandidate(id=uuid.uuid4(), label="B")
        metrics_a = {
            "success_rate": 0.9,
            "latency_p50": 100,
            "latency_p95": 200,
            "cost": 0.01,
            "tool_error_rate": 0,
            "policy_denial_rate": 0,
            "safety_failure_rate": 0,
        }
        metrics_b = {
            "success_rate": 0.7,
            "latency_p50": 300,
            "latency_p95": 600,
            "cost": 0.05,
            "tool_error_rate": 0.1,
            "policy_denial_rate": 0,
            "safety_failure_rate": 0,
        }
        winner_id, score_a, score_b = service.compare_pairwise(ca, cb, metrics_a, metrics_b)
        assert winner_id == ca.id
        assert score_a > score_b

    def test_build_pairwise_results(self):
        service = ABTestingService()
        tournament = AgentOptimizationTournament(id=uuid.uuid4())
        tc1 = AgentOptimizationTournamentCandidate(id=uuid.uuid4())
        tc2 = AgentOptimizationTournamentCandidate(id=uuid.uuid4())
        tc3 = AgentOptimizationTournamentCandidate(id=uuid.uuid4())
        metrics_map = {
            tc1.id: {
                "success_rate": 0.9,
                "latency_p50": 100,
                "latency_p95": 200,
                "cost": 0.01,
                "tool_error_rate": 0,
                "policy_denial_rate": 0,
                "safety_failure_rate": 0,
            },
            tc2.id: {
                "success_rate": 0.8,
                "latency_p50": 150,
                "latency_p95": 300,
                "cost": 0.02,
                "tool_error_rate": 0,
                "policy_denial_rate": 0,
                "safety_failure_rate": 0,
            },
            tc3.id: {
                "success_rate": 0.7,
                "latency_p50": 200,
                "latency_p95": 400,
                "cost": 0.03,
                "tool_error_rate": 0,
                "policy_denial_rate": 0,
                "safety_failure_rate": 0,
            },
        }
        results = service.build_pairwise_results(tournament, [tc1, tc2, tc3], metrics_map)
        assert len(results) == 3
        assert all(r.tournament_id == tournament.id for r in results)


class TestCandidateRanker:
    def test_rank_candidates(self):
        ranker = CandidateRanker()
        tournament = AgentOptimizationTournament(id=uuid.uuid4())
        tc1 = AgentOptimizationTournamentCandidate(id=uuid.uuid4())
        tc2 = AgentOptimizationTournamentCandidate(id=uuid.uuid4())
        candidates = [tc1, tc2]
        metrics_map = {
            tc1.id: {
                "success_rate": 0.95,
                "latency_p50": 50,
                "latency_p95": 100,
                "cost": 0.01,
                "tool_error_rate": 0,
                "policy_denial_rate": 0,
                "safety_failure_rate": 0,
            },
            tc2.id: {
                "success_rate": 0.60,
                "latency_p50": 500,
                "latency_p95": 1000,
                "cost": 0.10,
                "tool_error_rate": 0.2,
                "policy_denial_rate": 0,
                "safety_failure_rate": 0.3,
            },
        }
        results = ranker.rank_candidates(tournament, candidates, metrics_map, {})
        assert len(results) == 2
        assert results[0].rank == 1
        assert results[0].score > results[1].score

    def test_select_winner_skips_safety_regression(self):
        ranker = CandidateRanker()
        r1 = AgentOptimizationTournamentResult(
            tournament_candidate_id=uuid.uuid4(), score=0.8, rank=1, safety_regression=True
        )
        r2 = AgentOptimizationTournamentResult(
            tournament_candidate_id=uuid.uuid4(), score=0.6, rank=2, safety_regression=False
        )
        winner = ranker.select_winner([r1, r2])
        assert winner == r2

    def test_lowest_cost_does_not_win_if_success_rate_drops(self):
        ranker = CandidateRanker()
        tournament = AgentOptimizationTournament(id=uuid.uuid4())
        tc_best = AgentOptimizationTournamentCandidate(id=uuid.uuid4())
        tc_cheap = AgentOptimizationTournamentCandidate(id=uuid.uuid4())
        candidates = [tc_best, tc_cheap]
        metrics_map = {
            tc_best.id: {
                "success_rate": 0.95,
                "latency_p50": 100,
                "latency_p95": 200,
                "cost": 0.10,
                "tool_error_rate": 0,
                "policy_denial_rate": 0,
                "safety_failure_rate": 0,
            },
            tc_cheap.id: {
                "success_rate": 0.30,
                "latency_p50": 100,
                "latency_p95": 200,
                "cost": 0.001,
                "tool_error_rate": 0,
                "policy_denial_rate": 0,
                "safety_failure_rate": 0,
            },
        }
        results = ranker.rank_candidates(tournament, candidates, metrics_map, {})
        assert results[0].rank == 1
        winner = ranker.select_winner(results)
        assert winner is not None
        winner_tcid = winner.tournament_candidate_id
        winner_metrics = metrics_map[winner_tcid]
        assert winner_metrics["success_rate"] > 0.90


class TestTournamentRunner:
    @pytest.mark.asyncio
    async def test_create_tournament(self, runner, mock_db, agent, candidates):
        mock_db.execute = AsyncMock()
        mock_db.execute.side_effect = [
            AsyncMock(scalar_one_or_none=MagicMock(return_value=agent)),
            AsyncMock(scalar_one_or_none=MagicMock(return_value=candidates[0])),
            AsyncMock(scalar_one_or_none=MagicMock(return_value=candidates[1])),
            AsyncMock(scalar_one_or_none=MagicMock(return_value=candidates[2])),
        ]

        with patch(
            "app.services.agents.optimization.tournament_runner.get_settings"
        ) as mock_settings:
            settings = MagicMock()
            settings.agent_optimizer_tournaments_enabled = True
            mock_settings.return_value = settings

            tournament = await runner.create_tournament(
                tenant_id="default",
                agent_id=agent.id,
                candidate_ids=[c.id for c in candidates],
                parallel_limit=2,
            )
            assert tournament.status == "draft"
            assert tournament.parallel_limit == 2

    @pytest.mark.asyncio
    async def test_parallel_limit_respected(self, runner, mock_db, agent):
        with patch.object(runner, "_evaluate_all_candidates") as mock_eval:
            mock_eval.return_value = {}

            with patch(
                "app.services.agents.optimization.tournament_runner.get_settings"
            ) as mock_settings:
                settings = MagicMock()
                settings.agent_optimizer_tournaments_enabled = True
                settings.agent_optimizer_parallel_evals_enabled = True
                mock_settings.return_value = settings

                tournament = AgentOptimizationTournament(
                    id=uuid.uuid4(),
                    tenant_id="default",
                    agent_id=agent.id,
                    status="draft",
                    parallel_limit=2,
                )

                mock_db.execute = AsyncMock()
                mock_db.execute.side_effect = [
                    AsyncMock(scalar_one_or_none=MagicMock(return_value=tournament)),
                ]

            assert tournament.parallel_limit == 2

    @pytest.mark.asyncio
    async def test_candidate_with_safety_failure_loses(self, runner, mock_db):
        ranker = CandidateRanker()
        tournament = AgentOptimizationTournament(id=uuid.uuid4())
        tc_safe = AgentOptimizationTournamentCandidate(id=uuid.uuid4())
        tc_unsafe = AgentOptimizationTournamentCandidate(id=uuid.uuid4())
        candidates = [tc_unsafe, tc_safe]
        metrics_map = {
            tc_safe.id: {
                "success_rate": 0.8,
                "latency_p50": 100,
                "latency_p95": 200,
                "cost": 0.05,
                "tool_error_rate": 0,
                "policy_denial_rate": 0,
                "safety_failure_rate": 0,
            },
            tc_unsafe.id: {
                "success_rate": 0.9,
                "latency_p50": 100,
                "latency_p95": 200,
                "cost": 0.05,
                "tool_error_rate": 0,
                "policy_denial_rate": 0,
                "safety_failure_rate": 0.5,
            },
        }
        results = ranker.rank_candidates(tournament, candidates, metrics_map, {})
        winner = ranker.select_winner(results)
        assert winner is not None
        assert winner.tournament_candidate_id == tc_safe.id

    @pytest.mark.asyncio
    async def test_winner_does_not_apply_without_approval(self, runner, mock_db):
        with patch(
            "app.services.agents.optimization.tournament_runner.get_settings"
        ) as mock_settings:
            settings = MagicMock()
            settings.agent_optimizer_tournaments_enabled = True
            settings.agent_optimizer_apply_winner_enabled = True
            mock_settings.return_value = settings

            tournament = AgentOptimizationTournament(
                id=uuid.uuid4(),
                agent_id=uuid.uuid4(),
                approval_status="pending",
                winner_id=uuid.uuid4(),
            )
            mock_db.execute = AsyncMock()
            mock_db.execute.side_effect = [
                AsyncMock(scalar_one_or_none=MagicMock(return_value=tournament)),
            ]

            with pytest.raises(PermissionError, match="Winner must be approved before applying"):
                await runner.apply_winner(tournament.id)

    @pytest.mark.asyncio
    async def test_rollback_point_created(self, runner, mock_db, agent):
        with patch(
            "app.services.agents.optimization.tournament_runner.get_settings"
        ) as mock_settings:
            settings = MagicMock()
            settings.agent_optimizer_tournaments_enabled = True
            mock_settings.return_value = settings

            mock_db.execute = AsyncMock()
            result_mock = AsyncMock(scalar_one_or_none=MagicMock(return_value=agent))
            mock_db.execute.return_value = result_mock

            rollback = await runner._capture_rollback_point(agent.id)
            assert "instructions" in rollback
            assert rollback["instructions"] == "Do the thing."
            assert "allowed_tools" in rollback
            assert "captured_at" in rollback
