import os
from typing import Any

import yaml


class ComplianceControlMapperService:
    def __init__(self, mapping_path: str = "compliance/mappings/soc2_iso27001_control_map.yaml"):
        self.mapping_path = mapping_path
        self._data = self._load_data()

    def _load_data(self) -> dict[str, Any]:
        if not os.path.exists(self.mapping_path):
            return {"controls": []}
        with open(self.mapping_path) as f:
            return yaml.safe_load(f)

    def list_controls(self, framework: str | None = None) -> list[dict[str, Any]]:
        controls = self._data.get("controls", [])
        if framework:
            return [c for c in controls if c["framework"] == framework]
        return controls

    def get_control(self, framework: str, control_id: str) -> dict[str, Any] | None:
        for c in self._data.get("controls", []):
            if c["framework"] == framework and c["control_id"] == control_id:
                return c
        return None

    def validate_control(self, control: dict[str, Any]):
        if not control.get("owner_role"):
            raise ValueError(f"Control {control.get('control_id')} is missing an owner role")
        if not control.get("evidence_sources") or len(control.get("evidence_sources")) == 0:
            raise ValueError(f"Control {control.get('control_id')} is missing evidence sources")

        # Secret scanning in description or title (basic)
        for field in ["title", "description"]:
            val = control.get(field, "")
            if "PRIVATE KEY" in val or "API_KEY" in val:
                raise ValueError(
                    f"Control {control.get('control_id')} contains sensitive info in {field}"
                )

    def get_readiness_summary(self, framework: str) -> dict[str, Any]:
        controls = self.list_controls(framework)
        if not controls:
            return {}

        total = len(controls)
        implemented = len([c for c in controls if c["implementation_status"] == "implemented"])
        partial = len([c for c in controls if c["implementation_status"] == "partial"])

        return {
            "framework": framework,
            "total_controls": total,
            "implemented": implemented,
            "partial": partial,
            "readiness_percentage": (implemented / total * 100) if total > 0 else 0,
        }
