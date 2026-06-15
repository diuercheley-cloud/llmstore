from datetime import UTC, datetime
from typing import Any

from app.core.config import get_settings


class CommercialLiveBalancer:
    def __init__(self):
        self.settings = get_settings()

    def analyze_cluster_profitability(self, cluster_metrics: dict) -> float:
        """Calculate the profitability score of a cluster."""
        margin = cluster_metrics.get("margin_percent", 0.0)
        return margin

    def detect_flapping(self, cluster_id: str, proposed_change: float, history: list[dict]) -> bool:
        """Detect if applying the change would cause route flapping."""
        if not history:
            return False

        recent_changes = [h for h in history if h.get("cluster_id") == cluster_id]
        if not recent_changes:
            return False

        last_change = recent_changes[-1]
        last_time = last_change.get("timestamp")

        if last_time:
            now = datetime.now(UTC)
            diff_minutes = (now - last_time).total_seconds() / 60
            if diff_minutes < self.settings.commercial_live_balancing_min_stable_minutes:
                return True

        # Check if we are oscillating directions
        last_dir = last_change.get("change_percent", 0) > 0
        curr_dir = proposed_change > 0
        if last_dir != curr_dir:
            return True

        return False

    def apply_hysteresis(self, current_traffic: float, target_traffic: float) -> float:
        """Apply hysteresis to prevent micro-adjustments."""
        diff = abs(target_traffic - current_traffic)
        if diff < self.settings.commercial_live_balancing_hysteresis_percent:
            return current_traffic  # No change
        return target_traffic

    def calculate_balancing_delta(self, current_traffic: float, target_traffic: float) -> float:
        """Calculate the safe delta to apply in one cycle."""
        max_change = self.settings.commercial_live_balancing_max_traffic_change_percent
        diff = target_traffic - current_traffic

        if diff > max_change:
            return max_change
        elif diff < -max_change:
            return -max_change
        return diff

    def recommend_rebalance(
        self, source_cluster: str, metrics: dict, history: list[dict], qos_tier: Any | None = None
    ) -> dict[str, Any]:
        """Generate a recommendation for rebalancing traffic."""
        if not self.settings.commercial_live_balancing_enabled:
            return {"action": "none", "reason": "disabled"}

        # Phase 20: QoS Tier Enforcement
        if qos_tier:
            # If current latency violates QoS tier, decrease traffic even if margin is ok
            latency = metrics.get("avg_latency_ms", 0)
            if latency > qos_tier.max_p95_latency_ms:
                return {
                    "action": "decrease",
                    "reason": f"qos_latency_violation_{latency}ms",
                    "current_latency": latency,
                    "target_decrease_percent": self.settings.commercial_live_balancing_max_traffic_change_percent
                    * 1.5,  # More aggressive
                }

        margin = metrics.get("margin_percent", 0.0)
        if margin < self.settings.commercial_live_balancing_min_margin_percent:
            return {
                "action": "decrease",
                "reason": "low_margin",
                "current_margin": margin,
                "target_decrease_percent": self.settings.commercial_live_balancing_max_traffic_change_percent,
            }

        return {"action": "none", "reason": "stable"}

    def simulate_rebalance(self, current_state: dict, recommendation: dict) -> dict[str, Any]:
        """Simulate the effect of a rebalance recommendation."""
        current_traffic = current_state.get("traffic_percent", 100)

        if recommendation["action"] == "decrease":
            delta = -recommendation.get("target_decrease_percent", 0)
        elif recommendation["action"] == "increase":
            delta = recommendation.get("target_increase_percent", 0)
        else:
            delta = 0

        new_traffic = max(0, min(100, current_traffic + delta))

        return {
            "original_traffic": current_traffic,
            "simulated_traffic": new_traffic,
            "delta": delta,
        }

    def summarize_balancing_opportunities(self, clusters_metrics: list[dict]) -> list[dict]:
        """Find opportunities across multiple clusters."""
        opportunities = []
        for cluster in clusters_metrics:
            margin = cluster.get("margin_percent", 0.0)
            latency = cluster.get("avg_latency_ms", 0)

            if margin < self.settings.commercial_live_balancing_min_margin_percent:
                opportunities.append(
                    {
                        "cluster_id": cluster["cluster_id"],
                        "type": "cost_optimization",
                        "reason": f"Margin {margin}% below threshold {self.settings.commercial_live_balancing_min_margin_percent}%",
                    }
                )
            elif latency > self.settings.commercial_live_balancing_max_latency_ms:
                opportunities.append(
                    {
                        "cluster_id": cluster["cluster_id"],
                        "type": "latency_optimization",
                        "reason": f"Latency {latency}ms above threshold {self.settings.commercial_live_balancing_max_latency_ms}ms",
                    }
                )

        return opportunities
