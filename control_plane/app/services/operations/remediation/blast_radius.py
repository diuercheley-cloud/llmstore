from typing import Dict, Any

class RemediationBlastRadiusService:
    """
    Calculates the blast radius of a remediation plan deterministically.
    Advisory-only.
    """

    def calculate_blast_radius(self, inputs: Dict[str, Any]) -> str:
        """
        Determines the blast radius based on involved domains and risk level.
        """
        involved_domains = inputs.get("involved_domains", [])
        risk_level = inputs.get("risk_level", "low")
        
        if risk_level == "critical" or len(involved_domains) > 5:
            return "critical"
        elif risk_level == "high" or len(involved_domains) > 3:
            return "high"
        elif risk_level == "medium" or len(involved_domains) > 1:
            return "medium"
        else:
            return "low"

    def explain_blast_radius(self, inputs: Dict[str, Any]) -> str:
        """
        Provides an explanation for the calculated blast radius.
        """
        radius = self.calculate_blast_radius(inputs)
        involved_domains = inputs.get("involved_domains", [])
        
        explanation = f"Blast radius is {radius.upper()} because "
        if radius == "critical":
            explanation += f"the risk level is CRITICAL or {len(involved_domains)} domains are affected."
        elif radius == "high":
            explanation += f"the risk level is HIGH or {len(involved_domains)} domains are affected."
        elif radius == "medium":
            explanation += f"{len(involved_domains)} domains are affected."
        else:
            explanation += "only one domain is affected and risk is low."
            
        return explanation
