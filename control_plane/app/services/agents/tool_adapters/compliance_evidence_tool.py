from typing import Any, Dict

from app.services.agents.tool_adapter_contract import ToolAdapterContract


class ComplianceEvidenceToolAdapter(ToolAdapterContract):
    @property
    def name(self) -> str:
        return "compliance_evidence_tool"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "policy_id": {"type": "string"},
                "evidence_type": {"type": "string"}
            },
            "required": ["policy_id", "evidence_type"]
        }

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "evidence_id": {"type": "string"},
                "timestamp": {"type": "string"}
            }
        }

    @property
    def side_effect_level(self) -> str:
        return "write"

    async def execute(self, **kwargs) -> Dict[str, Any]:
        return {
            "evidence_id": "ev-998877",
            "timestamp": "2026-05-22T10:00:00Z"
        }

    async def dry_run(self, **kwargs) -> Dict[str, Any]:
        return {"status": "dry_run", "message": f"Would collect evidence for policy {kwargs['policy_id']}"}

    async def rollback(self, invocation_id: str, **kwargs) -> Dict[str, Any]:
        return {"status": "success", "message": "Compliance evidence record invalidated."}

    async def healthcheck(self) -> bool:
        return True
