from __future__ import annotations

from typing import Any, Dict, List
from prometheus_client import REGISTRY
from app.core import metrics

class PlatformSLOService:
    def __init__(self):
        # SLO Thresholds
        self.thresholds = {
            "availability": 0.999,
            "p95_latency": 2.0,  # seconds
            "queue_wait_p95": 5.0, # seconds
            "error_rate": 0.01,
            "fallback_rate": 0.05,
            "cache_hit_ratio": 0.2,
            "model_activation_success": 0.99,
        }

    def get_slo_report(self) -> Dict[str, Any]:
        """
        Calculates a real-time SLO report based on in-memory Prometheus metrics.
        """
        report = {}
        
        # 1. API Availability & Error Rate
        requests_total = self._get_counter_sum("llm_requests_total")
        errors_total = self._get_counter_sum("llm_request_errors_total")
        
        availability = 1.0
        error_rate = 0.0
        if requests_total > 0:
            error_rate = errors_total / requests_total
            availability = 1.0 - error_rate
            
        report["api_availability"] = {
            "value": availability,
            "target": self.thresholds["availability"],
            "status": "ok" if availability >= self.thresholds["availability"] else "critical"
        }
        
        report["error_rate"] = {
            "value": error_rate,
            "target": self.thresholds["error_rate"],
            "status": "ok" if error_rate <= self.thresholds["error_rate"] else "warning"
        }

        # 2. Latency (p95 approx from histogram)
        # Note: True p95 requires Prometheus quantile calculation. 
        # Here we provide a simplified status based on observation counts.
        p95_latency = self._get_histogram_avg("llm_request_latency_seconds")
        report["p95_latency"] = {
            "value": p95_latency,
            "target": self.thresholds["p95_latency"],
            "status": "ok" if p95_latency <= self.thresholds["p95_latency"] else "warning"
        }

        # 3. Cache Hit Ratio
        hits = self._get_counter_sum("llm_cache_hits_total")
        misses = self._get_counter_sum("llm_cache_misses_total")
        cache_hit_ratio = 0.0
        if (hits + misses) > 0:
            cache_hit_ratio = hits / (hits + misses)
        
        report["cache_hit_ratio"] = {
            "value": cache_hit_ratio,
            "target": self.thresholds["cache_hit_ratio"],
            "status": "ok" if cache_hit_ratio >= self.thresholds["cache_hit_ratio"] else "warning"
        }

        # 4. Fallback Rate
        fallbacks = self._get_counter_sum("llm_routing_fallbacks_total")
        decisions = self._get_counter_sum("llm_routing_decisions_total")
        fallback_rate = 0.0
        if decisions > 0:
            fallback_rate = fallbacks / decisions
            
        report["provider_fallback_rate"] = {
            "value": fallback_rate,
            "target": self.thresholds["fallback_rate"],
            "status": "ok" if fallback_rate <= self.thresholds["fallback_rate"] else "warning"
        }
        
        # 5. Billing Accuracy Mode (Placeholder for logic)
        report["billing_accuracy_mode"] = {
            "mode": "estimated", # Should be dynamically determined
            "status": "ok"
        }

        return report

    def get_platform_health(self) -> Dict[str, Any]:
        """
        Aggregated platform health status.
        """
        slo = self.get_slo_report()
        
        # Check for critical failures
        rbac_denials = self._get_counter_sum("llm_rbac_denials_total")
        attestation_failures = self._get_counter_sum("llm_attestation_failures_total")
        hot_swap_failures = self._get_counter_sum("llm_model_hot_swap_failures_total")
        
        overall_status = "ok"
        critical_issues = []
        
        if slo["api_availability"]["status"] == "critical":
            overall_status = "critical"
            critical_issues.append("Low API availability")
            
        if attestation_failures > 0:
            overall_status = "warning"
            critical_issues.append(f"Attestation failures detected: {int(attestation_failures)}")
            
        if hot_swap_failures > 0:
            overall_status = "warning"
            critical_issues.append(f"Model hot swap failures: {int(hot_swap_failures)}")

        return {
            "status": overall_status,
            "critical_issues": critical_issues,
            "metrics": {
                "rbac_denials": int(rbac_denials),
                "attestation_failures": int(attestation_failures),
                "hot_swap_failures": int(hot_swap_failures)
            }
        }

    def _get_counter_sum(self, name: str) -> float:
        metric = REGISTRY.get_sample_value(f"{name}_total")
        return float(metric) if metric is not None else 0.0

    def _get_histogram_avg(self, name: str) -> float:
        sum_val = REGISTRY.get_sample_value(f"{name}_sum")
        count_val = REGISTRY.get_sample_value(f"{name}_count")
        if count_val and count_val > 0:
            return float(sum_val) / float(count_val)
        return 0.0
