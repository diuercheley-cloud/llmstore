import os
from datetime import UTC, datetime
from typing import Any

import yaml


class ISMSManagerService:
    def __init__(self, base_path: str = "compliance"):
        self.base_path = base_path

    def get_status(self) -> dict[str, Any]:
        policies = self.list_policies()
        risks = self.get_risk_register()
        soa = self.get_soa()

        return {
            "status": "readiness",
            "framework": "ISO 27001:2022",
            "policies_count": len(policies),
            "risks_count": len(risks.get("risks", [])),
            "soa_progress": self._calculate_soa_progress(soa),
            "last_updated": datetime.now(UTC).isoformat(),
        }

    def list_policies(self) -> list[dict[str, Any]]:
        policy_dir = os.path.join(self.base_path, "policies")
        if not os.path.exists(policy_dir):
            return []

        policies = []
        for file in os.listdir(policy_dir):
            if file.endswith(".md"):
                policies.append({"name": file, "path": os.path.join(policy_dir, file)})
        return policies

    def get_risk_register(self) -> dict[str, Any]:
        risk_path = os.path.join(self.base_path, "risk", "risk-register.yaml")
        if not os.path.exists(risk_path):
            return {"risks": []}
        with open(risk_path) as f:
            return yaml.safe_load(f)

    def get_soa(self) -> dict[str, Any]:
        soa_path = os.path.join(self.base_path, "risk", "statement-of-applicability.yaml")
        if not os.path.exists(soa_path):
            return {"controls": []}
        with open(soa_path) as f:
            return yaml.safe_load(f)

    def _calculate_soa_progress(self, soa: dict[str, Any]) -> float:
        controls = soa.get("controls", [])
        if not controls:
            return 0
        implemented = len([c for c in controls if c.get("status") == "implemented"])
        return (implemented / len(controls)) * 100

    def validate_policy(self, content: str):
        if "| **Owner** |" not in content:
            raise ValueError("Policy is missing an owner definition")
        if "| **Review Frequency** |" not in content:
            raise ValueError("Policy is missing review frequency")

    def validate_risk(self, risk: dict[str, Any]):
        if not risk.get("treatment_plan"):
            raise ValueError(f"Risk {risk.get('id')} is missing a treatment plan")

    def validate_soa_entry(self, entry: dict[str, Any]):
        if entry.get("included") and not entry.get("justification"):
            raise ValueError(
                f"SoA Control {entry.get('code')} is included but missing justification"
            )
        if entry.get("included") is None:
            raise ValueError(
                f"SoA Control {entry.get('code')} must specify if included or excluded"
            )
