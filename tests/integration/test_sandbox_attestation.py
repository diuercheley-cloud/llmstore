from app.services.agents.code_interpreter.sandbox_attestation import AttestationService


class _Profile:
    provider = "gvisor"
    kernel_isolation_level = "user-space-kernel"
    runtime_version = "runsc-1.0"
    network_mode = "none"
    filesystem_mode = "read-only"
    limits = {"cpu": 1, "memory_mb": 256}


def test_create_attestation_records_profile_metadata():
    attestation = AttestationService.create_attestation(
        profile=_Profile(),
        code="print('ok')",
        stdout="ok",
        stderr="",
        artifacts=["sha256:abc"],
    )

    assert attestation.provider == "gvisor"
    assert attestation.network_policy == "none"
    assert attestation.artifact_hashes == ["sha256:abc"]


def test_verify_attestation_requires_provider():
    assert AttestationService.verify_attestation({"provider": "firecracker"}) is True
    assert AttestationService.verify_attestation({}) is False
