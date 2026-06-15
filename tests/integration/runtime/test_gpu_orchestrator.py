import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.models.runtime.gpu_orchestration import AutoscalingPolicy
from app.services.gpu_orchestrator import GpuOrchestrator


@pytest.mark.asyncio
async def test_sync_local_gpus_no_nvidia_smi():
    mock_db = AsyncMock()
    service = GpuOrchestrator(mock_db)
    node_id = uuid.uuid4()

    # Mock subprocess.run to raise FileNotFoundError (simulate no nvidia-smi)
    with patch("subprocess.run", side_effect=FileNotFoundError):
        gpus = await service.sync_local_gpus(node_id)
        assert gpus == []


@pytest.mark.asyncio
async def test_sync_local_gpus_mocked_output():
    mock_db = AsyncMock()

    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_db.execute.return_value = mock_result

    service = GpuOrchestrator(mock_db)
    node_id = uuid.uuid4()

    mock_output = "0, NVIDIA RTX 4090, 24576, 1024, 10, 55"
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = mock_output
        mock_run.return_value.returncode = 0

        gpus = await service.sync_local_gpus(node_id)
        assert len(gpus) == 1
        assert gpus[0].name == "NVIDIA RTX 4090"
        assert gpus[0].memory_total_mb == 24576


@pytest.mark.asyncio
async def test_evaluate_autoscaling_no_policies():
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result

    service = GpuOrchestrator(mock_db)
    await service.evaluate_autoscaling()

    # Should not add any events
    assert not mock_db.add.called


@pytest.mark.asyncio
async def test_autoscaling_scale_up_recommendation():
    mock_db = AsyncMock()
    policy = AutoscalingPolicy(
        id=uuid.uuid4(),
        model_registry_id=uuid.uuid4(),
        name="test-policy",
        strategy="queue_depth",
        target_value=5.0,
        min_replicas=1,
        max_replicas=5,
        mode="recommendation",
    )
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [policy]
    mock_db.execute.return_value = mock_result

    service = GpuOrchestrator(mock_db)
    # Mocking _check_policy to return scale_up
    with patch.object(GpuOrchestrator, "_check_policy", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = {
            "action": "scale_up",
            "reason": "Queue depth too high",
            "replicas_before": 1,
            "replicas_after": 2,
            "metrics": {"queue_depth": 10},
        }

        await service.evaluate_autoscaling()
        assert mock_db.add.called
        # Check if AutoscalingEvent was added
        added_obj = mock_db.add.call_args[0][0]
        assert added_obj.event_type == "scale_up"
