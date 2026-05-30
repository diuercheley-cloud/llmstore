import pytest
import uuid
from fastapi import HTTPException
from app.core.config import get_settings
from app.services.mlops.dataset_registry import DatasetRegistry
from app.services.mlops.training_job_registry import TrainingJobRegistry
from app.services.mlops.finetuning_service import FineTuningService
from app.services.mlops.experiment_tracker import ExperimentTracker
from app.services.mlops.evaluation_artifacts import EvaluationArtifacts
from app.services.mlops.model_lineage import ModelLineage


@pytest.mark.asyncio
async def test_dataset_versionado(session):
    registry = DatasetRegistry(session)
    dataset = await registry.create_dataset(name="test-ds")
    assert dataset.is_production is False
    assert dataset.is_approved is True

    version = await registry.create_version(
        dataset_id=dataset.id,
        version="v1.0.0",
        checksum="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        provenance="s3://bucket/ds",
        content_bytes=b""
    )
    assert version.version == "v1.0.0"
    assert version.dataset_id == dataset.id


@pytest.mark.asyncio
async def test_checksum_invalido_detectado(session):
    registry = DatasetRegistry(session)
    dataset = await registry.create_dataset(name="test-checksum")

    with pytest.raises(HTTPException) as exc:
        await registry.create_version(
            dataset_id=dataset.id,
            version="v1.0.0",
            checksum="wrong_checksum",
            provenance="s3://bucket/ds",
            content_bytes=b"actual content"
        )
    assert exc.value.status_code == 400
    assert "Invalid dataset checksum" in exc.value.detail


@pytest.mark.asyncio
async def test_job_mock_executa(session):
    ds_reg = DatasetRegistry(session)
    dataset = await ds_reg.create_dataset(name="test-ft")
    version = await ds_reg.create_version(
        dataset_id=dataset.id,
        version="v1.0",
        checksum="hash",
        provenance="s3://bucket/ds"
    )

    ft_service = FineTuningService(session)
    job_id = await ft_service.start_fine_tuning(
        model_name="qwen-7b",
        dataset_version_id=version.id,
        provider="mock",
    )

    job_registry = TrainingJobRegistry(session)
    job = await job_registry.get_job(job_id)
    assert job.status == "completed"
    assert "qwen-7b-ft-" in job.output_model_id
    assert "[REDACTED_SENSITIVE_DATA]" in job.logs


@pytest.mark.asyncio
async def test_artifact_com_secret_bloqueado(session):
    tracker = ExperimentTracker(session)
    exp = await tracker.create_experiment(name="exp-artifact")
    run = await tracker.log_run(experiment_id=exp.id)

    eval_service = EvaluationArtifacts(session)
    # Registering sensitive data without policy -> raises 400
    with pytest.raises(HTTPException) as exc:
        await eval_service.register_artifact(
            run_id=run.id,
            name="eval_res",
            path="/metrics/eval.json",
            content="API key: dummy-key-12345678901234567890123456789012",
        )
    assert exc.value.status_code == 400
    assert "Sensitive data detected" in exc.value.detail

    # Registering with policy -> succeeds
    artifact = await eval_service.register_artifact(
        run_id=run.id,
        name="eval_res",
        path="/metrics/eval.json",
        content="API key: dummy-key-12345678901234567890123456789012",
        redaction_policy="strict_redact",
    )
    assert artifact.contains_sensitive_data is True
    assert artifact.is_redacted is True


@pytest.mark.asyncio
async def test_lineage_conecta_dataset_job_model(session):
    ds_reg = DatasetRegistry(session)
    dataset = await ds_reg.create_dataset(name="lineage-ds")
    version = await ds_reg.create_version(
        dataset_id=dataset.id,
        version="v1.0",
        checksum="hash",
        provenance="s3://bucket"
    )

    ft_service = FineTuningService(session)
    job_id = await ft_service.start_fine_tuning(
        model_name="gemma",
        dataset_version_id=version.id,
        provider="mock",
    )

    job_registry = TrainingJobRegistry(session)
    job = await job_registry.get_job(job_id)

    lineage_service = ModelLineage(session)
    lineage = await lineage_service.get_lineage(job.output_model_id)
    assert lineage is not None
    assert lineage.dataset_version_id == version.id
    assert lineage.training_job_id == job.id


@pytest.mark.asyncio
async def test_external_integration_disabled_por_default(session):
    # Ensure flags are default False
    settings = get_settings()
    assert settings.mlflow_integration_enabled is False
    assert settings.wandb_integration_enabled is False

    tracker = ExperimentTracker(session)
    exp = await tracker.create_experiment(name="exp-default")
    run = await tracker.log_run(experiment_id=exp.id)

    # In SQLite, log_run will log the event and details.
    # Let's inspect the AdminAuditEvent recorded
    from sqlalchemy import select
    from app.models.admin_rbac import AdminAuditEvent
    result = await session.execute(
        select(AdminAuditEvent).where(AdminAuditEvent.event_type == "experiment_run_log")
    )
    audit = result.scalars().first()
    assert audit is not None
    assert audit.metadata_json["integrations"]["mlflow_triggered"] is False
    assert audit.metadata_json["integrations"]["wandb_triggered"] is False


@pytest.mark.asyncio
async def test_mlops_endpoints_disabled_by_default(admin_client, admin_token_headers, monkeypatch):
    monkeypatch.setenv("MLOPS_ENABLED", "false")
    monkeypatch.setenv("FINE_TUNING_ENABLED", "false")
    monkeypatch.setenv("EXPERIMENT_TRACKING_ENABLED", "false")
    get_settings.cache_clear()

    # Create dataset -> 403
    resp = await admin_client.post(
        "/admin/mlops/datasets",
        json={"name": "test-endpoints", "description": "some text"},
        headers=admin_token_headers
    )
    assert resp.status_code == 403

    # Get datasets -> 403
    resp = await admin_client.get(
        "/admin/mlops/datasets",
        headers=admin_token_headers
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_mlops_endpoints_work_when_enabled(admin_client, admin_token_headers, monkeypatch, session):
    monkeypatch.setenv("MLOPS_ENABLED", "true")
    monkeypatch.setenv("FINE_TUNING_ENABLED", "true")
    monkeypatch.setenv("EXPERIMENT_TRACKING_ENABLED", "true")
    get_settings.cache_clear()

    # Create dataset -> 201
    resp = await admin_client.post(
        "/admin/mlops/datasets",
        json={"name": "test-enabled-ds", "description": "desc", "is_production": False},
        headers=admin_token_headers
    )
    assert resp.status_code == 201
    dataset_data = resp.json()
    dataset_id = dataset_data["id"]

    # List datasets -> 200
    resp = await admin_client.get(
        "/admin/mlops/datasets",
        headers=admin_token_headers
    )
    assert resp.status_code == 200
    assert any(d["id"] == dataset_id for d in resp.json())

    # Create dataset version -> 201
    resp = await admin_client.post(
        f"/admin/mlops/datasets/{dataset_id}/versions",
        json={
            "version": "v1.0.0",
            "checksum": "abc",
            "provenance": "manual",
            "redaction_status": "none"
        },
        headers=admin_token_headers
    )
    assert resp.status_code == 201
    version_data = resp.json()
    version_id = version_data["id"]

    # Create fine-tuning job -> 201
    resp = await admin_client.post(
        "/admin/mlops/fine-tuning/jobs",
        json={
            "model_name": "llama3",
            "dataset_version_id": version_id,
            "provider": "mock",
            "hyperparameters": {"epochs": 1}
        },
        headers=admin_token_headers
    )
    assert resp.status_code == 201
    job_data = resp.json()
    job_id = job_data["job_id"]

    # Get fine-tuning job status -> 200
    resp = await admin_client.get(
        f"/admin/mlops/fine-tuning/jobs/{job_id}",
        headers=admin_token_headers
    )
    assert resp.status_code == 200
    job_details = resp.json()
    assert job_details["status"] == "completed"
    output_model_id = job_details["output_model_id"]
    assert output_model_id is not None

    # Get model lineage -> 200
    resp = await admin_client.get(
        f"/admin/mlops/model-lineage/{output_model_id}",
        headers=admin_token_headers
    )
    assert resp.status_code == 200
    lineage_data = resp.json()
    assert lineage_data["model_id"] == output_model_id
    assert lineage_data["dataset_version_id"] == version_id
    assert lineage_data["training_job_id"] == job_id

