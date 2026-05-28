# Owner: agent-platform
import logging
import uuid
from typing import Dict, List, Tuple

from app.models.agent_optimization_tournament import (
    AgentOptimizationPairwiseResult,
    AgentOptimizationTournament,
    AgentOptimizationTournamentCandidate,
)

logger = logging.getLogger(__name__)


class ABTestingService:
    def __init__(self):
        self._pairwise_cache: Dict[str, float] = {}

    def compare_pairwise(
        self,
        candidate_a: AgentOptimizationTournamentCandidate,
        candidate_b: AgentOptimizationTournamentCandidate,
        metrics_a: Dict,
        metrics_b: Dict,
    ) -> Tuple[uuid.UUID, float, float]:
        score_a = self._compute_pairwise_score(metrics_a)
        score_b = self._compute_pairwise_score(metrics_b)

        if score_a >= score_b:
            winner_id = candidate_a.id
        else:
            winner_id = candidate_b.id

        return winner_id, score_a, score_b

    def _compute_pairwise_score(self, metrics: Dict) -> float:
        score = 0.0
        score += metrics.get("success_rate", 0) * 10.0
        score -= metrics.get("latency_p50", 0) / 1000.0
        score -= metrics.get("latency_p95", 0) / 1000.0
        score -= metrics.get("cost", 0) * 5.0
        score -= metrics.get("tool_error_rate", 0) * 8.0
        score -= metrics.get("policy_denial_rate", 0) * 8.0
        score -= metrics.get("safety_failure_rate", 0) * 20.0
        return round(score, 4)

    def build_pairwise_results(
        self,
        tournament: AgentOptimizationTournament,
        candidates: List[AgentOptimizationTournamentCandidate],
        metrics_map: Dict[uuid.UUID, Dict],
    ) -> List[AgentOptimizationPairwiseResult]:
        results = []
        for i in range(len(candidates)):
            for j in range(i + 1, len(candidates)):
                ca = candidates[i]
                cb = candidates[j]
                ma = metrics_map.get(ca.id, {})
                mb = metrics_map.get(cb.id, {})
                winner_id, score_a, score_b = self.compare_pairwise(ca, cb, ma, mb)

                result = AgentOptimizationPairwiseResult(
                    tournament_id=tournament.id,
                    candidate_a_id=ca.id,
                    candidate_b_id=cb.id,
                    winner_id=winner_id,
                    score_a=score_a,
                    score_b=score_b,
                )
                results.append(result)
        return results
