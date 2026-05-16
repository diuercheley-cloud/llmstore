import hashlib
import json
from typing import Any

RISK_THRESHOLDS: list[tuple[float, str]] = [
    (0.75, "critical"),
    (0.50, "high"),
    (0.25, "medium"),
]

FALLBACK_LEVEL = "low"

ADVISORY_RECOMMENDATIONS: dict[str, str] = {
    "low": (
        "No action required. Continue routine monitoring."
    ),
    "medium": (
        "Review signals. Consider investigation if trend persists or escalates."
    ),
    "high": (
        "Investigate root cause. Prepare mitigation plan. "
        "Approval workflow is recommended before any action."
    ),
    "critical": (
        "Requires human approval workflow. Do not auto-remediate. "
        "Escalate to operator immediately."
    ),
}

ADVISORY_REQUIRES_APPROVAL: dict[str, bool] = {
    "low": False,
    "medium": False,
    "high": True,
    "critical": True,
}


class FailureRiskScoringService:
    """Stateless, advisory-only risk scoring service for Phase 69.

    Classifies risk scores into levels and builds deterministic,
    sanitized assessments. Never triggers or suggests auto-remediation.
    """

    @staticmethod
    def classify_risk(score: float) -> str:
        """Map a numeric risk score to a risk level string.

        Thresholds:
            >= 0.75  -> critical
            >= 0.50  -> high
            >= 0.25  -> medium
            <  0.25  -> low
        """
        if not isinstance(score, (int, float)):
            return FALLBACK_LEVEL
        for threshold, level in RISK_THRESHOLDS:
            if score >= threshold:
                return level
        return FALLBACK_LEVEL

    @staticmethod
    def recommendation_for_level(risk_level: str) -> str:
        """Return a deterministic, sanitized recommendation string.

        The returned string is always a fixed template — never includes
        raw user input or sensitive data.
        """
        if not isinstance(risk_level, str):
            risk_level = FALLBACK_LEVEL
        level = risk_level.strip().lower()
        return ADVISORY_RECOMMENDATIONS.get(level, ADVISORY_RECOMMENDATIONS[FALLBACK_LEVEL])

    def build_assessment(
        self,
        forecast: dict[str, Any],
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Build an advisory-only risk assessment from a forecast dict.

        Parameters
        ----------
        forecast : dict
            Output from ``DeterministicFailureForecastingEngine.forecast``.
            Must contain at least ``risk_score``; optionally
            ``forecast_type``, ``explanation``, ``input_hash``.
        dry_run : bool
            When True (default) the assessment explicitly signals that no
            action should be taken.

        Returns
        -------
        dict
            Assessment with keys: risk_level, risk_score, recommendation,
            requires_approval, dry_run, advisory_only, immutable_hash,
            deterministic_version.
        """
        risk_score_raw = forecast.get("risk_score", 0.0)
        try:
            risk_score = float(risk_score_raw) if risk_score_raw is not None else 0.0
        except (TypeError, ValueError):
            risk_score = 0.0
        risk_level = self.classify_risk(risk_score)
        recommendation = self.recommendation_for_level(risk_level)
        requires_approval = ADVISORY_REQUIRES_APPROVAL[risk_level]

        assessment: dict[str, Any] = {
            "forecast_type": forecast.get("forecast_type", "unknown"),
            "risk_score": round(float(risk_score), 4),
            "risk_level": risk_level,
            "recommendation": recommendation,
            "requires_approval": requires_approval,
            "dry_run": bool(dry_run),
            "advisory_only": True,
            "deterministic_version": forecast.get("deterministic_version", "v1"),
            "input_hash": forecast.get("input_hash", ""),
        }

        assessment["immutable_hash"] = self._compute_assessment_hash(assessment)
        return assessment

    @staticmethod
    def _compute_assessment_hash(assessment: dict[str, Any]) -> str:
        """Deterministic SHA-256 of the core assessment fields."""
        core = {k: assessment[k] for k in ("risk_level", "recommendation", "requires_approval", "dry_run", "advisory_only") if k in assessment}
        raw = json.dumps(core, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
