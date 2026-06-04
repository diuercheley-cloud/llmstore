from unittest.mock import AsyncMock, MagicMock

import pytest
from app.core.config import get_settings
from app.services.agents.code_interpreter.providers.docker_sandbox import DockerSandboxProvider
from app.services.agents.code_interpreter.sandbox_policy import SandboxPolicyViolation
from app.services.agents.code_interpreter.sandbox_runtime import SandboxRuntime


@pytest.mark.asyncio
async def test_sandbox_runtime_provider_selection(monkeypatch):
    settings = get_settings()
    db = MagicMock()
    runtime = SandboxRuntime(db)

    monkeypatch.setattr(settings, "agent_code_sandbox_docker_enabled", True)
    provider = runtime._get_provider()
    assert provider.name == "docker"

    monkeypatch.setattr(settings, "agent_code_sandbox_provider", "docker")
    monkeypatch.setattr(settings, "agent_code_sandbox_docker_enabled", True)
    provider = runtime._get_provider()
    assert provider.name == "docker"

    monkeypatch.setattr(settings, "agent_code_sandbox_provider", "firecracker")
    monkeypatch.setattr(settings, "agent_code_sandbox_firecracker_enabled", True)
    provider = runtime._get_provider()
    assert provider.name == "firecracker"

    monkeypatch.setattr(settings, "agent_code_sandbox_provider", "gvisor")
    monkeypatch.setattr(settings, "agent_code_sandbox_gvisor_enabled", True)
    provider = runtime._get_provider()
    assert provider.name == "gvisor"


@pytest.mark.asyncio
async def test_microvm_required_blocks_docker(monkeypatch):
    settings = get_settings()
    db = MagicMock()
    runtime = SandboxRuntime(db)

    monkeypatch.setattr(settings, "agent_code_sandbox_provider", "docker")
    monkeypatch.setattr(settings, "agent_code_sandbox_microvm_required", True)

    with pytest.raises(RuntimeError, match="Docker sandbox is blocked because MicroVM isolation is required"):
        runtime._get_provider()


@pytest.mark.asyncio
async def test_sandbox_without_attestation_fails_in_production(monkeypatch):
    settings = get_settings()
    db = MagicMock()
    runtime = SandboxRuntime(db)

    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "agent_code_sandbox_provider", "mock")
    mock_provider = MagicMock()
    mock_provider.run = AsyncMock(
        return_value={"stdout": "test", "stderr": "", "exit_code": 0, "artifacts": []}
    )
    mock_provider.name = "mock"
    monkeypatch.setattr(runtime, "_get_provider", lambda: mock_provider)

    with pytest.raises(RuntimeError, match="did not report kernel_isolation_level"):
        await runtime.execute("print(1)")


@pytest.mark.asyncio
async def test_docker_attestation_created(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/docker")
    mock_proc = MagicMock()
    mock_proc.communicate = AsyncMock(return_value=(b"output", b""))
    mock_proc.returncode = 0
    monkeypatch.setattr("asyncio.create_subprocess_exec", AsyncMock(return_value=mock_proc))
    provider = DockerSandboxProvider()

    class FakeLimits:
        memory_limit_mb = 128
        writable_tmp_size_mb = 64
        timeout_seconds = 30
        max_output_size_bytes = 4096

        def model_dump(self):
            return {"memory_limit_mb": 128, "timeout_seconds": 30}

    result = await provider.run("print(1)", FakeLimits())
    assert result["provider"] == "docker"
    assert result["kernel_isolation_level"] == "container-shared-kernel"
    assert result["network_mode"] == "none"
    assert result["filesystem_mode"] == "read-only-rootfs"


@pytest.mark.asyncio
async def test_readiness_report(monkeypatch):
    settings = get_settings()
    db = MagicMock()
    runtime = SandboxRuntime(db)

    monkeypatch.setattr(settings, "agent_code_sandbox_provider", "firecracker")
    monkeypatch.setattr(settings, "agent_code_sandbox_firecracker_enabled", True)
    monkeypatch.setattr(settings, "agent_code_sandbox_microvm_required", True)
    monkeypatch.setattr(
        "app.services.agents.code_interpreter.microvm_policy.shutil.which",
        lambda name: "/usr/bin/firecracker" if name == "firecracker" else None,
    )

    report = await runtime.check_readiness()
    assert report["sandbox_provider_available"] is True
    assert report["provider"] == "firecracker"
    assert report["provider_configured"] is True
    assert report["provider_healthy"] is True
    assert report["microvm_required"] is True
    assert report["fallback_blocked"] is True


@pytest.mark.asyncio
async def test_firecracker_disabled_does_not_initialize(monkeypatch):
    settings = get_settings()
    runtime = SandboxRuntime(MagicMock())

    monkeypatch.setattr(settings, "agent_code_sandbox_provider", "firecracker")
    monkeypatch.setattr(settings, "agent_code_sandbox_firecracker_enabled", False)

    with pytest.raises(RuntimeError, match="firecracker sandbox provider is disabled by feature flag"):
        runtime._get_provider()


@pytest.mark.asyncio
async def test_gvisor_disabled_does_not_initialize(monkeypatch):
    settings = get_settings()
    runtime = SandboxRuntime(MagicMock())

    monkeypatch.setattr(settings, "agent_code_sandbox_provider", "gvisor")
    monkeypatch.setattr(settings, "agent_code_sandbox_gvisor_enabled", False)

    with pytest.raises(RuntimeError, match="gvisor sandbox provider is disabled by feature flag"):
        runtime._get_provider()


@pytest.mark.asyncio
async def test_attestation_is_created_for_each_execution(monkeypatch):
    settings = get_settings()
    runtime = SandboxRuntime(MagicMock())

    monkeypatch.setattr(settings, "agent_code_sandbox_provider", "mock")
    result = await runtime.execute("print('ok')")

    assert result["provider"] == "mock"
    assert result["attestation"]["provider"] == "mock"
    assert result["attestation"]["network_mode"] == "none"
    assert set(result["attestation"]["artifact_hashes"]) >= {"code", "stdout", "stderr"}


@pytest.mark.asyncio
async def test_docker_continues_working_in_dev_with_mocked_runtime(monkeypatch):
    settings = get_settings()
    runtime = SandboxRuntime(MagicMock())

    monkeypatch.setattr(settings, "app_env", "local")
    monkeypatch.setattr(settings, "agent_code_sandbox_provider", "docker")
    monkeypatch.setattr(settings, "agent_code_sandbox_docker_enabled", True)

    provider = MagicMock()
    provider.name = "docker"
    provider.mock = False
    provider.run = AsyncMock(
        return_value={
            "stdout": "hello\n",
            "stderr": "",
            "exit_code": 0,
            "execution_time_ms": 1,
            "provider": "docker",
            "kernel_isolation_level": "container-shared-kernel",
            "network_mode": "none",
            "filesystem_mode": "read-only-rootfs",
            "artifacts": [],
        }
    )
    monkeypatch.setattr(runtime, "_get_provider", lambda: provider)

    result = await runtime.execute("print('hello')")
    assert result["provider"] == "docker"
    assert result["attestation"]["provider"] == "docker"


@pytest.mark.asyncio
async def test_network_attempt_is_blocked_by_default():
    runtime = SandboxRuntime(MagicMock())

    with pytest.raises(SandboxPolicyViolation, match="Network access is disabled by default"):
        await runtime.execute("print('https://example.com')")
