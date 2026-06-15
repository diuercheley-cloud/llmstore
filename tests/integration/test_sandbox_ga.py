import pytest
from app.core.config import get_settings
from app.services.agents.code_interpreter.providers.firecracker_sandbox import (
    FirecrackerSandboxProvider,
)
from app.services.agents.code_interpreter.providers.gvisor_sandbox import GVisorSandboxProvider
from app.services.agents.code_interpreter.sandbox_attestation import AttestationService
from app.services.agents.code_interpreter.sandbox_policy import (
    SandboxPolicyEngine,
    SandboxPolicyViolation,
)


@pytest.mark.asyncio
async def test_gvisor_indisponivel_nao_retorna_sucesso_simulado():
    settings = get_settings()
    settings.agent_code_sandbox_gvisor_enabled = True
    provider = GVisorSandboxProvider()
    try:
        res = await provider.run("print(1)", None)
        assert res.get("status") == "provider_unavailable"
    except RuntimeError as e:
        assert "runsc/docker is not available" in str(e) or "gVisor provider is required" in str(e)


@pytest.mark.asyncio
async def test_firecracker_indisponivel_nao_retorna_sucesso_simulado():
    settings = get_settings()
    settings.agent_code_sandbox_firecracker_enabled = True
    provider = FirecrackerSandboxProvider()
    try:
        res = await provider.run("print(1)", None)
        assert res.get("status") == "provider_unavailable"
    except RuntimeError as e:
        assert "firecracker binary is not available" in str(
            e
        ) or "Firecracker provider is required" in str(e)


@pytest.mark.asyncio
async def test_production_bloqueia_mock_simulation():
    settings = get_settings()
    settings.agent_sandbox_allow_simulated_provider = False
    policy = SandboxPolicyEngine()
    with pytest.raises(SandboxPolicyViolation, match="Simulated provider 'mock' is not allowed"):
        policy.validate_provider("mock", is_simulated=True)


@pytest.mark.asyncio
async def test_microvm_required_bloqueia_docker():
    settings = get_settings()
    settings.agent_code_sandbox_microvm_required = True
    policy = SandboxPolicyEngine()
    with pytest.raises(SandboxPolicyViolation, match="MicroVM isolation is required"):
        policy.validate_provider("docker", is_simulated=False)


def test_attestation_ausente_falha():
    settings = get_settings()
    settings.agent_sandbox_production_requires_attestation = True
    settings.app_env = "production"
    assert AttestationService.verify_attestation({"provider": "gvisor", "signature": ""}) is False
    assert (
        AttestationService.verify_attestation(
            {"provider": "gvisor", "signature": "placeholder-signature-fallback"}
        )
        is False
    )


def test_tentativa_de_network_e_bloqueada():
    policy = SandboxPolicyEngine()
    code = "import urllib.request\nurllib.request.urlopen('http://example.com')"
    with pytest.raises(SandboxPolicyViolation, match="Import of 'urllib' is not allowed"):
        policy.validate_code(code)

    code2 = "import socket"
    with pytest.raises(SandboxPolicyViolation, match="Import of 'socket' is not allowed"):
        policy.validate_code(code2)

    code3 = "import requests"
    with pytest.raises(SandboxPolicyViolation, match="Import of 'requests' is not allowed"):
        policy.validate_code(code3)


def test_tentativa_de_ler_env_e_bloqueada():
    policy = SandboxPolicyEngine()
    code = "file_path = '.env'"
    with pytest.raises(SandboxPolicyViolation, match="Access to protected path is not allowed"):
        policy.validate_code(code)


def test_tentativa_de_acessar_docker_sock_e_bloqueada():
    policy = SandboxPolicyEngine()
    code = "sock = '/var/run/docker.sock'"
    with pytest.raises(SandboxPolicyViolation, match="Access to protected path is not allowed"):
        policy.validate_code(code)
