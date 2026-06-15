import pytest
from app.contracts.attestation import (
    AttestationCapabilities,
    AttestationContract,
    AttestationReport,
)


class MockAttestation(AttestationContract):
    async def generate_report(self) -> AttestationReport:
        return AttestationReport(
            subject="test",
            timestamp="now",
            measurements={},
            policy_result="passed",
            signature="sig",
            certificate_chain="cert",
        )

    async def verify_report(self, report: AttestationReport) -> bool:
        return report.policy_result == "passed"

    def capabilities(self) -> AttestationCapabilities:
        return AttestationCapabilities(hardware_trust=True)

    def validate_contract(self) -> bool:
        return True


@pytest.mark.asyncio
async def test_attestation_contract_implementation():
    attestation = MockAttestation()
    assert attestation.validate_contract() is True

    report = await attestation.generate_report()
    assert report.subject == "test"

    is_valid = await attestation.verify_report(report)
    assert is_valid is True

    caps = attestation.capabilities()
    assert caps.hardware_trust is True
