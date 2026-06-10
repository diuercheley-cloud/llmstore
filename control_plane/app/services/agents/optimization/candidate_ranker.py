# Owner: agent-platform
import logging
import uuid
from typing import Dict, List, Optional, Tuple

from app.models.agents.agent_optimization_tournament import (
    AgentOptimizationTournament,
    AgentOptimizationTournamentCandidate,
    AgentOptimizationTournamentResult,
)
from app.services.agents.optimization.statistical_scoring import StatisticalScoringService

logger = logging.getLogger(__name__)


class CandidateRanker:
    def __init__(self, scoring_service: Optional[StatisticalScoringService] = None):
        self.scoring = scoring_service or StatisticalScoringService()

    def rank_candidates(
        self,
        tournament: AgentOptimizationTournament,
        candidates: List[AgentOptimizationTournamentCandidate],
        metrics_map: Dict[uuid.UUID, Dict],
        baseline_metrics: Dict,
    ) -> List[AgentOptimizationTournamentResult]:
        scored: List[Tuple[float, int, AgentOptimizationTournamentCandidate, Dict]] = []

        for idx, candidate in enumerate(candidates):
            raw_metrics = metrics_map.get(candidate.id, {})
            deltas = self.scoring.compute_baseline_deltas(raw_metrics, baseline_metrics)
            penalties = self.scoring.compute_penalties(deltas, raw_metrics)

            score = 0.0
            weights = StatisticalScoringService.WEIGHTS

            score += raw_metrics.get("success_rate", 0) * weights["success_rate"]
            score -= raw_metrics.get("latency_p50", 0) / 5000.0 * weights["latency_p50"]
            score -= raw_metrics.get("latency_p95", 0) / 5000.0 * weights["latency_p95"]
            score -= raw_metrics.get("cost", 0) * 2.0 * weights["cost"]
            score -= raw_metrics.get("tool_error_rate", 0) * weights["tool_error_rate"]
            score -= raw_metrics.get("policy_denial_rate", 0) * weights["policy_denial_rate"]
            score -= (
                raw_metrics.get("safety_failure_rate", 0)
                * 2.0
                * weights["safety_failure_rate"]
            )

            score += penalties
            scored.append((score, idx, candidate, raw_metrics))

        scored.sort(key=lambda x: (-x[0], x[1]))

        results = []
        for rank, (score, _, candidate, raw_metrics) in enumerate(scored, start=1):
            result = AgentOptimizationTournamentResult(
                tournament_id=tournament.id,
                tournament_candidate_id=candidate.id,
                metrics=raw_metrics,
                score=round(score, 4),
                rank=rank,
                safety_regression=raw_metrics.get("safety_failure_rate", 0) > 0,
            )
            results.append(result)

        return results

    def select_winner(
        self,
        results: List[AgentOptimizationTournamentResult],
    ) -> Optional[AgentOptimizationTournamentResult]:
        if not results:
            return None
        for r in results:
            if r.safety_regression:
                continue
            return r
        return results[0]

    def build_ranking_list(self, results: List[AgentOptimizationTournamentResult]) -> List[Dict]:
        return [
            {
                "tournament_candidate_id": str(r.tournament_candidate_id),
                "rank": r.rank,
                "score": r.score,
                "safety_regression": r.safety_regression,
            }
            for r in results
        ]
