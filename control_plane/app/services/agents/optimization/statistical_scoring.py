# Owner: agent-platform
import statistics


class StatisticalScoringService:
    WEIGHTS = {
        "success_rate": 0.30,
        "latency_p50": 0.15,
        "latency_p95": 0.10,
        "cost": 0.15,
        "tool_error_rate": 0.10,
        "policy_denial_rate": 0.10,
        "safety_failure_rate": 0.10,
    }

    PENALTIES = {
        "safety_regression": -0.50,
        "cost_spike": -0.25,
        "latency_spike": -0.20,
        "tool_misuse": -0.15,
    }

    def compute_metric_summary(self, raw_metrics: list[dict]) -> dict[str, float]:
        if not raw_metrics:
            return {}

        summary = {}
        keys = [
            "success_rate",
            "latency_p50",
            "latency_p95",
            "cost",
            "tool_error_rate",
            "policy_denial_rate",
            "safety_failure_rate",
        ]
        for key in keys:
            values = [m.get(key, 0.0) for m in raw_metrics if key in m]
            if values:
                summary[key] = statistics.mean(values)
                summary[f"{key}_p50"] = statistics.median(values)
                if len(values) > 1:
                    sorted_vals = sorted(values)
                    idx = int(len(sorted_vals) * 0.95)
                    summary[f"{key}_p95"] = sorted_vals[min(idx, len(sorted_vals) - 1)]
                else:
                    summary[f"{key}_p95"] = values[0]
        return summary

    def compute_baseline_deltas(
        self, candidate_metrics: dict, baseline_metrics: dict
    ) -> dict[str, float]:
        deltas = {}
        for key in [
            "success_rate",
            "latency_p50",
            "latency_p95",
            "cost",
            "tool_error_rate",
            "policy_denial_rate",
            "safety_failure_rate",
        ]:
            base_val = baseline_metrics.get(key, 0.0)
            cand_val = candidate_metrics.get(key, 0.0)
            if key == "success_rate":
                deltas[key] = cand_val - base_val
            else:
                deltas[key] = cand_val - base_val
        return deltas

    def compute_penalties(self, deltas: dict, raw_metrics: dict) -> float:
        total_penalty = 0.0

        if (
            raw_metrics.get("safety_failure_rate", 0) > 0
            or deltas.get("safety_failure_rate", 0) > 0
        ):
            total_penalty += self.PENALTIES["safety_regression"]

        cost_delta = deltas.get("cost", 0)
        if cost_delta > 0.10:
            total_penalty += self.PENALTIES["cost_spike"]

        latency_delta = deltas.get("latency_p50", 0)
        if latency_delta > 100:
            total_penalty += self.PENALTIES["latency_spike"]

        tool_error_delta = deltas.get("tool_error_rate", 0)
        if tool_error_delta > 0.05:
            total_penalty += self.PENALTIES["tool_misuse"]

        return total_penalty

    def compute_confidence_score(self, all_scores: list[float], winner_score: float) -> float:
        if len(all_scores) < 2:
            return 0.5
        sorted_scores = sorted(all_scores, reverse=True)
        margin = winner_score - sorted_scores[1] if len(sorted_scores) > 1 else 1.0
        normalized_margin = max(0.0, min(1.0, margin / 0.5))
        return round(0.5 + 0.5 * normalized_margin, 4)
