import os
import yaml
from datetime import datetime
from typing import Any, Dict, List, Optional

class ISMSManagerService:
    def __init__(self, base_path: str = "compliance"):
        self.base_path = base_path

    def get_status(self) -> Dict[str, Any]:
        policies = self.list_policies()
        risks = self.get_risk_register()
        soa = self.get_soa()
        
        return {
            "status": "readiness",
            "framework": "ISO 27001:2022",
            "policies_count": len(policies),
            "risks_count": len(risks.get("risks", [])),
            "soa_progress": self._calculate_soa_progress(soa),
            "last_updated": datetime.utcnow().isoformat()
        }

    def list_policies(self) -> List[Dict[str, Any]]:
        policy_dir = os.path.join(self.base_path, "policies")
        if not os.path.exists(policy_dir):
            return []
            
        policies = []
        for file in os.listdir(policy_dir):
            if file.endswith(".md"):
                policies.append({
                    "name": file,
                    "path": os.path.join(policy_dir, file)
                })
        return policies

    def get_risk_register(self) -> Dict[str, Any]:
        risk_path = os.path.join(self.base_path, "risk", "risk-register.yaml")
        if not os.path.exists(risk_path):
            return {"risks": []}
        with open(risk_path, "r") as f:
            return yaml.safe_load(f)

    def get_soa(self) -> Dict[str, Any]:
        soa_path = os.path.join(self.base_path, "risk", "statement-of-applicability.yaml")
        if not os.path.exists(soa_path):
            return {"controls": []}
        with open(soa_path, "r") as f:
            return yaml.safe_load(f)

    def _calculate_soa_progress(self, soa: Dict[str, Any]) -> float:
        controls = soa.get("controls", [])
        if not controls: return 0
        implemented = len([c for c in controls if c.get("status") == "implemented"])
        return (implemented / len(controls)) * 100

    def validate_policy(self, content: str):
        if "| **Owner** |" not in content:
            raise ValueError("Policy is missing an owner definition")
        if "| **Review Frequency** |" not in content:
            raise ValueError("Policy is missing review frequency")

    def validate_risk(self, risk: Dict[str, Any]):
        if not risk.get("treatment_plan"):
            raise ValueError(f"Risk {risk.get('id')} is missing a treatment plan")

    def validate_soa_entry(self, entry: Dict[str, Any]):
        if entry.get("included") and not entry.get("justification"):
            raise ValueError(f"SoA Control {entry.get('code')} is included but missing justification")
        if entry.get("included") is None:
            raise ValueError(f"SoA Control {entry.get('code')} must specify if included or excluded")
