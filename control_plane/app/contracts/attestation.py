from typing import Any, Protocol, runtime_checkable

from app.contracts.base import BaseContract, ContractCapability
from pydantic import BaseModel


class AttestationReport(BaseModel):
    subject: str
    timestamp: str
    measurements: dict[str, Any]
    policy_result: str
    signature: str
    certificate_chain: str


class AttestationCapabilities(ContractCapability):
    hardware_trust: bool = False
    pki_integration: bool = False
    enforcement_mode: bool = False


@runtime_checkable
class AttestationContract(BaseContract, Protocol):
    """
    Contract for System and Node Attestation.
    """

    async def generate_report(self) -> AttestationReport:
        """Generates a new attestation report for the current node."""
        ...

    async def verify_report(self, report: AttestationReport) -> bool:
        """Verifies an existing attestation report."""
        ...

    def capabilities(self) -> AttestationCapabilities:
        """Returns attestation capabilities."""
        ...

    def validate_contract(self) -> bool:
        required_methods = ["generate_report", "verify_report", "capabilities"]
        for method in required_methods:
            if not hasattr(self, method) or not callable(getattr(self, method)):
                return False
        return True
