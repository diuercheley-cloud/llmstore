# Owner: agent-platform
import logging
from typing import Any, Dict, List


class HallucinationChecker:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def check(self, candidate_response: str, evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyzes consistency between the response and tool/memory evidence.
        """
        findings = []
        
        # Heuristic: if response mentions numbers not in evidence
        # (In real implementation, this would use a small NLI model or LLM-as-a-judge)
        
        # Placeholder for unsupported claims
        if not evidence and len(candidate_response) > 100:
             findings.append({
                 "checker_type": "hallucination",
                 "severity": "medium",
                 "description": "Long response generated with zero supporting evidence retrieved.",
                 "evidence": {"evidence_count": 0}
             })
             
        return findings
