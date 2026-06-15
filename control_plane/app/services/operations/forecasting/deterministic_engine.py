import hashlib
import json
from datetime import UTC, datetime
from typing import Any


class DeterministicFailureForecastingEngine:
    """Stateless, deterministic failure forecasting engine for Phase 69.

    Produces fully reproducible forecasts from the same input signals.
    No ML, no network calls, no randomness, no implicit current time.
    """

    DETERMINISTIC_VERSION = "v1"

    SEVERITY_WEIGHTS: dict[str, float] = {
        "info": 0.1,
        "warning": 0.4,
        "error": 0.6,
        "critical": 0.8,
    }

    @staticmethod
    def normalize_signals(signals: list[dict]) -> list[dict]:
        """Normalize raw signal dicts to a standardized internal format."""
        normalized: list[dict] = []
        for s in signals:
            entry: dict[str, Any] = {
                "signal_type": str(s.get("signal_type", "unknown")),
                "source_domain": str(s.get("source_domain", "unknown")),
                "severity": str(s.get("severity", "info")),
                "confidence": float(s.get("confidence", 0.0)),
                "observed_at": s.get("observed_at"),
                "payload": s.get("payload_json") or s.get("payload"),
            }
            normalized.append(entry)
        return normalized

    @staticmethod
    def compute_input_hash(signals: list[dict]) -> str:
        """Compute deterministic SHA-256 hash of signal list.

        Same input always produces the same hash regardless of order
        (sorted_keys) or locale.
        """
        raw = json.dumps(signals, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def forecast(
        self,
        signals: list[dict],
        window_minutes: int = 60,
        reference_time: datetime | None = None,
        forecast_type: str = "aggregate_failure_risk",
    ) -> dict[str, Any]:
        """Produce a deterministic forecast from the given signals.

        Parameters
        ----------
        signals : list[dict]
            Raw signal dicts (keys match FailureSignal model fields).
        window_minutes : int
            Lookback window for recency weighting.
        reference_time : datetime or None
            Explicit reference time.  When None the max observed_at across
            all signals is used (or UNIX epoch if no timestamps exist).
        forecast_type : str
            Label for the forecast output.

        Returns
        -------
        dict
            forecast with keys: forecast_type, risk_score, confidence,
            deterministic_version, input_hash, explanation, advisory_only.
        """
        normalized = self.normalize_signals(signals)
        input_hash = self.compute_input_hash(normalized)

        if not normalized:
            return self._zero_risk_forecast(forecast_type, input_hash)

        timestamps = [s["observed_at"] for s in normalized if s["observed_at"] is not None]
        if reference_time is None:
            reference_time = max(timestamps) if timestamps else datetime(1970, 1, 1, tzinfo=UTC)

        severity_scores: list[float] = []
        type_counts: dict[str, int] = {}
        domains: set[str] = set()

        for s in normalized:
            severity_scores.append(self.SEVERITY_WEIGHTS.get(s["severity"], 0.1))
            st = s["signal_type"]
            type_counts[st] = type_counts.get(st, 0) + 1
            domains.add(s["source_domain"])

        base_risk = sum(severity_scores) / len(severity_scores)

        recency_factor = 1.0
        recent_count = sum(
            1
            for s in normalized
            if _is_within_window(s["observed_at"], reference_time, window_minutes)
        )
        if recent_count > 0:
            recency_factor = 1.0 + (recent_count / len(normalized)) * 0.5

        repetition_factor = 1.0
        for count in type_counts.values():
            if count > 1:
                repetition_factor += (count - 1) * 0.2
        repetition_factor = min(repetition_factor, 2.0)

        domain_count = len(domains)
        confidence = min(0.5 + domain_count * 0.1, 0.95)

        risk_score = min(base_risk * recency_factor * repetition_factor, 1.0)

        explanation = {
            "signal_count": len(normalized),
            "unique_domains": domain_count,
            "recent_signals_in_window": recent_count,
            "base_risk": _round4(base_risk),
            "recency_factor": _round4(recency_factor),
            "repetition_factor": _round4(repetition_factor),
            "effective_risk_score": _round4(risk_score),
            "effective_confidence": _round4(confidence),
            "rule": (
                "risk = min(base_risk * recency_factor * repetition_factor, 1.0); "
                "confidence = min(0.5 + unique_domains * 0.1, 0.95); "
                "advisory_only = true"
            ),
        }

        return {
            "forecast_type": forecast_type,
            "risk_score": _round4(risk_score),
            "confidence": _round4(confidence),
            "deterministic_version": self.DETERMINISTIC_VERSION,
            "input_hash": input_hash,
            "explanation": explanation,
            "advisory_only": True,
        }

    def explain_forecast(self, forecast: dict) -> str:
        """Return a human-readable summary of a forecast dict."""
        lines = [
            f"Forecast type: {forecast.get('forecast_type', 'unknown')}",
            f"Risk score: {forecast.get('risk_score', 0)}",
            f"Confidence: {forecast.get('confidence', 0)}",
            f"Advisory only: {forecast.get('advisory_only', True)}",
            f"Deterministic version: {forecast.get('deterministic_version', 'N/A')}",
            f"Input hash: {forecast.get('input_hash', 'N/A')}",
        ]
        expl = forecast.get("explanation", {})
        if isinstance(expl, dict):
            for k, v in expl.items():
                lines.append(f"  {k}: {v}")
        else:
            lines.append(f"  details: {expl}")
        return "\n".join(lines)

    def _zero_risk_forecast(self, forecast_type: str, input_hash: str) -> dict:
        return {
            "forecast_type": forecast_type,
            "risk_score": 0.0,
            "confidence": 1.0,
            "deterministic_version": self.DETERMINISTIC_VERSION,
            "input_hash": input_hash,
            "explanation": {"note": "No signals provided — zero risk."},
            "advisory_only": True,
        }


def _round4(value: float) -> float:
    return round(value, 4)


def _is_within_window(
    observed_at: Any,
    reference_time: datetime,
    window_minutes: int,
) -> bool:
    if not isinstance(observed_at, datetime):
        return False
    diff = (reference_time - observed_at).total_seconds() / 60.0
    return 0 <= diff <= window_minutes
