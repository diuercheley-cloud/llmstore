import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional


class DeterministicOperationsCorrelationEngine:
    """
    Deterministic engine for correlating operational events across domains.
    Guarantees reproducibility: Same input events produce the same correlation output.
    Does not use ML, external networks, or implicit side effects like current time.
    """

    def normalize_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sorts and cleans events to ensure deterministic processing.
        Events should have: event_type, source_domain, source_ref, severity, timestamp.
        """
        # We sort by timestamp, then domain, then type, then ref to ensure order independence
        sorted_events = sorted(
            events,
            key=lambda e: (str(e.get("timestamp", "")), str(e.get("source_domain", "")), str(e.get("event_type", "")), str(e.get("source_ref", "")))
        )
        return sorted_events

    def build_correlation_key(self, events: List[Dict[str, Any]]) -> str:
        """
        Generates a unique, deterministic key based on the normalized events.
        """
        if not events:
            return "empty_correlation"
        
        # Build a string representing the participants
        participants = []
        for e in events:
            participants.append(f"{e.get('source_domain')}:{e.get('event_type')}")
        
        raw_str = "|".join(participants)
        return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()[:16]

    def correlate(self, events: List[Dict[str, Any]], forecasts: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Performs deterministic correlation analysis.
        """
        if not events:
            return {
                "correlation_type": "none",
                "correlation_score": 0.0,
                "confidence": 0.0,
                "involved_domains": [],
                "correlation_key": "empty",
                "explanation": "No events provided for correlation.",
                "advisory_only": True
            }

        normalized = self.normalize_events(events)
        involved_domains = sorted(list(set(e.get("source_domain") for e in normalized)))
        
        # 1. Multi-domain bonus
        domain_count = len(involved_domains)
        domain_bonus = min(0.4, (domain_count - 1) * 0.1) if domain_count > 1 else 0.0

        # 2. Severity scoring
        severity_map = {"info": 0.1, "warning": 0.4, "error": 0.8, "critical": 1.0}
        total_severity = sum(severity_map.get(str(e.get("severity", "info")).lower(), 0.1) for e in normalized)
        avg_severity = total_severity / len(normalized)

        # 3. Temporal Proximity (deterministic)
        # We calculate the window size. Smaller windows increase the score.
        timestamps = []
        for e in normalized:
            ts = e.get("timestamp")
            if isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except ValueError:
                    continue
            if isinstance(ts, datetime):
                timestamps.append(ts.timestamp())
        
        time_bonus = 0.0
        if len(timestamps) > 1:
            window = max(timestamps) - min(timestamps)
            # Window < 1 min -> 0.2 bonus, Window > 1 hour -> 0.0 bonus
            if window < 60:
                time_bonus = 0.2
            elif window < 3600:
                time_bonus = 0.2 * (1 - (window / 3600))

        # 4. Recurrence / Repetition
        # Multiple events of the same type/domain increase confidence
        type_counts = {}
        for e in normalized:
            k = f"{e.get('source_domain')}:{e.get('event_type')}"
            type_counts[k] = type_counts.get(k, 0) + 1
        
        repetition_bonus = min(0.2, (len(normalized) - len(type_counts)) * 0.05)

        # 5. Forecast Alignment
        forecast_bonus = 0.0
        if forecasts:
            # If any event domain matches a forecast domain, increase score
            forecast_domains = set(f.get("target_domain") for f in forecasts)
            if any(d in forecast_domains for d in involved_domains):
                forecast_bonus = 0.15

        # Final Score Calculation (capped at 1.0)
        base_score = avg_severity
        final_score = min(1.0, base_score + domain_bonus + time_bonus + repetition_bonus + forecast_bonus)
        
        # Confidence depends on event volume and domain diversity
        confidence = min(0.95, (len(normalized) * 0.1) + (domain_count * 0.1))

        # Correlation Type logic
        if domain_count > 1:
            correlation_type = "cross_domain_impact"
        elif avg_severity > 0.7:
            correlation_type = "high_severity_cluster"
        else:
            correlation_type = "operational_pattern"

        correlation_key = self.build_correlation_key(normalized)
        
        explanation = self.explain_correlation({
            "correlation_type": correlation_type,
            "involved_domains": involved_domains,
            "event_count": len(normalized),
            "avg_severity": avg_severity,
            "time_bonus": time_bonus,
            "domain_bonus": domain_bonus
        })

        return {
            "correlation_type": correlation_type,
            "correlation_score": round(final_score, 4),
            "confidence": round(confidence, 4),
            "involved_domains": involved_domains,
            "correlation_key": correlation_key,
            "explanation": explanation,
            "advisory_only": True
        }

    def explain_correlation(self, data: Dict[str, Any]) -> str:
        """
        Generates a human-readable explanation for the correlation.
        """
        domains = ", ".join(data.get("involved_domains", []))
        count = data.get("event_count", 0)
        
        msg = f"Detected {data.get('correlation_type')} involving domains: [{domains}]. "
        msg += f"Correlated {count} events with an average severity of {data.get('avg_severity', 0):.2f}. "
        
        if data.get("domain_bonus", 0) > 0:
            msg += "Cross-domain interaction detected. "
        if data.get("time_bonus", 0) > 0:
            msg += "High temporal proximity observed. "
            
        return msg.strip()
