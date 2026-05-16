from app.services.operations.compatibility_contracts.verification import CompatibilityVerificationService


def test_verification_respects_replay_safe_and_warnings():
    service = CompatibilityVerificationService()
    contract = service.verify_contract({"compatibility_status": "deprecated", "schema_version": "1.0.0"})
    matrix = service.verify_matrix(
        {
            "compatibility_type": "forward",
            "compatibility_status": "warning",
            "upgrade_supported": False,
            "downgrade_supported": False,
            "replay_safe": True,
        }
    )
    negotiation = service.verify_negotiation({"negotiated_version": None, "negotiation_status": "conflicted", "replay_verifiable": False})
    assert contract["verification_status"] == "warning"
    assert matrix["verification_status"] == "warning"
    assert negotiation["verification_status"] == "failed"
