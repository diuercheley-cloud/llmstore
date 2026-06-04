from typing import Any

from app.services.operations.compatibility_contracts.capability_negotiation import (
    CapabilityNegotiationService,
)
from app.services.operations.compatibility_contracts.compatibility_matrix import (
    CompatibilityMatrixService,
)
from app.services.operations.compatibility_contracts.semantic_versioning import (
    SemanticVersioningService,
)
from app.services.operations.compatibility_contracts.validation import validate_schema_compatibility


class CompatibilityVerificationService:
    def __init__(self) -> None:
        self.semver = SemanticVersioningService()
        self.matrix_service = CompatibilityMatrixService()
        self.capabilities = CapabilityNegotiationService()

    def verify_contract(self, contract: Any) -> dict[str, Any]:
        status = self._get(contract, "compatibility_status")
        schema_result = validate_schema_compatibility(
            self._get(contract, "schema_version"),
            self._get(contract, "schema_version"),
        )
        verification_status = "passed"
        if status == "blocked":
            verification_status = "failed"
        elif status == "deprecated":
            verification_status = "warning"
        return {
            "verification_type": "contract",
            "verification_status": verification_status,
            "replay_safe": True,
            "compatibility_summary": f"contract_status={status}; schema={schema_result['summary']}",
        }

    def verify_matrix(self, matrix: dict[str, Any]) -> dict[str, Any]:
        if not matrix["replay_safe"] or matrix["compatibility_status"] == "incompatible":
            status = "failed"
        elif matrix["compatibility_status"] == "warning" and matrix["compatibility_type"] == "forward":
            status = "warning"
        else:
            status = "passed"
        return {
            "verification_type": "matrix",
            "verification_status": status,
            "replay_safe": matrix["replay_safe"],
            "compatibility_summary": self.matrix_service.explain_matrix(matrix),
        }

    def verify_negotiation(self, session: Any) -> dict[str, Any]:
        status = self._get(session, "negotiation_status")
        replay_safe = bool(self._get(session, "replay_verifiable"))
        if status in {"rejected", "conflicted"} or not replay_safe:
            verification_status = "failed"
        else:
            verification_status = "passed"
        return {
            "verification_type": "negotiation",
            "verification_status": verification_status,
            "replay_safe": replay_safe,
            "compatibility_summary": (
                f"negotiated_version={self._get(session, 'negotiated_version')}; "
                f"status={status}"
            ),
        }

    def verify_capabilities(self, result: dict[str, Any]) -> dict[str, Any]:
        valid = self.capabilities.validate_capabilities(result)
        if not valid:
            status = "failed"
        elif result["negotiation_status"] == "partially_approved":
            status = "warning"
        elif result["negotiation_status"] == "denied":
            status = "failed"
        else:
            status = "passed"
        return {
            "verification_type": "capabilities",
            "verification_status": status,
            "replay_safe": True,
            "compatibility_summary": self.capabilities.explain_capabilities(result),
        }

    def explain_verification(self, result: dict[str, Any]) -> str:
        return (
            f"type={result['verification_type']}; status={result['verification_status']}; "
            f"replay_safe={result['replay_safe']}; summary={result['compatibility_summary']}"
        )

    @staticmethod
    def _get(item: Any, key: str) -> Any:
        return item[key] if isinstance(item, dict) else getattr(item, key)
