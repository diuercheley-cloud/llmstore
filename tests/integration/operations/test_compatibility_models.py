from app.models.operations.compatibility_contracts import (
    CapabilityNegotiation,
    CompatibilityContract,
    CompatibilityMatrix,
    CompatibilityReceipt,
    CompatibilityVerificationResult,
    DeprecationLifecycle,
    FeatureCompatibilityFlag,
    VersionNegotiationSession,
)


def test_compatibility_models_exposed():
    assert CompatibilityContract.__tablename__ == "compatibility_contracts"
    assert CompatibilityMatrix.__tablename__ == "compatibility_matrices"
    assert VersionNegotiationSession.__tablename__ == "version_negotiation_sessions"
    assert CapabilityNegotiation.__tablename__ == "capability_negotiations"
    assert FeatureCompatibilityFlag.__tablename__ == "feature_compatibility_flags"
    assert DeprecationLifecycle.__tablename__ == "deprecation_lifecycles"
    assert CompatibilityVerificationResult.__tablename__ == "compatibility_verification_results"
    assert CompatibilityReceipt.__tablename__ == "compatibility_receipts"


def test_phase_78_migration_present():
    content = open(
        "control_plane/alembic/versions/phase78_compatibility_contracts.py", encoding="utf-8"
    ).read()
    assert "compatibility_contracts" in content
    assert "version_negotiation_sessions" in content
