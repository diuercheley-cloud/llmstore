import uuid
from unittest.mock import MagicMock, patch

import pytest
from app.models.commercial.commercial_infra_simulation import CommercialInfrastructureSimulation
from app.services.routing.infra_adapters.local_gpu_adapter import LocalGPUAdapter
from app.services.routing.infra_adapters.proxmox_adapter import ProxmoxAdapter


@pytest.fixture
def mock_settings():
    with (
        patch("app.services.routing.infra_adapters.proxmox_adapter.get_settings") as m1,
        patch("app.services.routing.infra_adapters.local_gpu_adapter.get_settings") as m2,
    ):
        settings = MagicMock()
        settings.commercial_proxmox_execution_enabled = False
        settings.commercial_proxmox_api_url = "https://pve.local:8006"
        settings.commercial_proxmox_node = "node1"
        settings.commercial_proxmox_token_id = "user!token"
        settings.commercial_proxmox_token_secret = "secret"
        settings.commercial_proxmox_allowed_vm_ids = "100,101"
        settings.commercial_proxmox_allowed_ct_ids = "200"
        settings.commercial_proxmox_dry_run = True

        settings.commercial_local_gpu_execution_enabled = False
        settings.commercial_local_gpu_dry_run = True
        settings.commercial_local_gpu_allowed_actions = "inspect,metrics"

        m1.return_value = settings
        m2.return_value = settings
        yield settings


@pytest.mark.asyncio
async def test_proxmox_adapter_disabled(mock_settings):
    adapter = ProxmoxAdapter()
    assert adapter.validate_connection() is False

    sim = CommercialInfrastructureSimulation(
        id=uuid.uuid4(), simulation_type="start_vm", target_identifier="100"
    )
    result = await adapter.execute_action(sim)
    assert result["status"] == "failed"
    assert "disabled" in result["error"]


@pytest.mark.asyncio
async def test_proxmox_adapter_allowlist(mock_settings):
    mock_settings.commercial_proxmox_execution_enabled = True
    adapter = ProxmoxAdapter()

    sim = CommercialInfrastructureSimulation(
        id=uuid.uuid4(),
        simulation_type="start_vm",
        target_identifier="999",  # Not in allowlist
    )
    result = await adapter.execute_action(sim)
    assert result["status"] == "failed"
    assert "allowlist" in result["error"]


@pytest.mark.asyncio
async def test_proxmox_adapter_dry_run(mock_settings):
    mock_settings.commercial_proxmox_execution_enabled = True
    adapter = ProxmoxAdapter()

    sim = CommercialInfrastructureSimulation(
        id=uuid.uuid4(), simulation_type="start_vm", target_identifier="100"
    )
    result = await adapter.execute_action(sim, dry_run=True)
    assert result["status"] == "dry_run"
    assert result["vmid"] == "100"


@pytest.mark.asyncio
async def test_proxmox_adapter_real_execution(mock_settings):
    mock_settings.commercial_proxmox_execution_enabled = True
    mock_settings.commercial_proxmox_dry_run = False
    adapter = ProxmoxAdapter()

    sim = CommercialInfrastructureSimulation(
        id=uuid.uuid4(), simulation_type="start_vm", target_identifier="100"
    )

    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 202
        mock_post.return_value.json.return_value = {"data": "UPID:node1:00001234:..."}

        result = await adapter.execute_action(sim, dry_run=False)
        assert result["status"] == "executed"
        assert result["external_id"] == "UPID:node1:00001234:..."


@pytest.mark.asyncio
async def test_local_gpu_adapter_disabled(mock_settings):
    adapter = LocalGPUAdapter()
    assert adapter.validate_connection() is False

    sim = CommercialInfrastructureSimulation(
        id=uuid.uuid4(), simulation_type="metrics", target_identifier="gpu0"
    )
    result = await adapter.execute_action(sim)
    assert result["status"] == "failed"
    assert "disabled" in result["error"]


@pytest.mark.asyncio
async def test_local_gpu_adapter_metrics_parsing(mock_settings):
    mock_settings.commercial_local_gpu_execution_enabled = True
    adapter = LocalGPUAdapter()

    fake_output = "0, NVIDIA GeForce RTX 3080, 50, 20, 10240, 2048, 8192, 65, 150"

    with (
        patch("shutil.which", return_value="/usr/bin/nvidia-smi"),
        patch("subprocess.run") as mock_run,
    ):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = fake_output

        result = adapter.collect_gpu_metrics()
        assert result["status"] == "executed"
        assert len(result["gpus"]) == 1
        assert result["gpus"][0]["name"] == "NVIDIA GeForce RTX 3080"
        assert result["gpus"][0]["utilization_gpu"] == 50.0


@pytest.mark.asyncio
async def test_local_gpu_adapter_blocked_actions(mock_settings):
    mock_settings.commercial_local_gpu_execution_enabled = True
    mock_settings.commercial_local_gpu_dry_run = False
    # Add to allowed actions but it should still be blocked internally
    mock_settings.commercial_local_gpu_allowed_actions = "inspect,metrics,kill_process"
    adapter = LocalGPUAdapter()

    sim = CommercialInfrastructureSimulation(
        id=uuid.uuid4(),
        simulation_type="kill_process",  # Strictly blocked
        target_identifier="1234",
        requested_action_json={"pid": 1234},
    )
    result = await adapter.execute_action(sim, dry_run=False)
    assert result["status"] == "failed"
    assert "blocked" in result["error"]
