from typing import Any, Dict, List, Optional
import hashlib

class OperationalCorrelationRiskAnalysisService:
    """
    Advisory-only risk analysis service for operational correlations.
    Strictly follows deterministic rules and never initiates remediation or enforcement.
    """

    def classify_operational_risk(self, correlation_score: float, confidence: float) -> str:
        """
        Classifies operational risk level based on score and confidence.
        Deterministic and stateless.
        """
        # Confidence acts as a filter: low confidence risks are always 'low'
        if confidence < 0.4:
            return "low"
        
        if correlation_score < 0.3:
            return "low"
        elif correlation_score < 0.6:
            return "medium"
        elif correlation_score < 0.85:
            return "high"
        else:
            return "critical"

    def analyze_correlation_risk(self, correlation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyzes a correlation and generates an advisory risk assessment.
        """
        score = correlation.get("correlation_score", 0.0)
        confidence = correlation.get("confidence", 0.0)
        domains = correlation.get("involved_domains", [])
        
        risk_level = self.classify_operational_risk(score, confidence)
        
        # Determine if approval workflow should be suggested
        # Suggest approval for high/critical risks with high confidence
        suggest_approval = risk_level in ["high", "critical"] and confidence > 0.7
        
        assessment = {
            "risk_level": risk_level,
            "correlation_key": correlation.get("correlation_key"),
            "advisory_only": True,
            "dry_run": True,
            "suggest_approval_workflow": suggest_approval,
            "involved_domains": domains,
            "recommendation": self.build_advisory_summary(risk_level, domains, suggest_approval)
        }
        
        # Deterministic integrity hash for the assessment
        raw_assessment = f"{risk_level}:{suggest_approval}:{','.join(sorted(domains))}"
        assessment["assessment_hash"] = hashlib.sha256(raw_assessment.encode("utf-8")).hexdigest()[:32]
        
        return assessment

    def build_advisory_summary(self, risk_level: str, domains: List[str], suggest_approval: bool) -> str:
        """
        Builds a human-readable advisory summary with deterministic recommendations.
        """
        domain_str = ", ".join(domains)
        
        if risk_level == "low":
            return f"Low operational risk detected in domains: [{domain_str}]. Monitor for pattern changes."
        
        if risk_level == "medium":
            return f"Moderate correlation detected between [{domain_str}]. Inspect relevant logs for early signs of instability."
        
        recommendation = f"High risk operational pattern identified involving [{domain_str}]. "
        if risk_level == "critical":
            recommendation = f"CRITICAL operational risk detected between domains [{domain_str}]. Immediate manual inspection is advised. "
        
        if suggest_approval:
            recommendation += "Consider initiating a formal manual approval workflow for any configuration changes in these domains."
        else:
            recommendation += "Increase monitoring granularity and verify tenant isolation status."
            
        return recommendation.strip()
