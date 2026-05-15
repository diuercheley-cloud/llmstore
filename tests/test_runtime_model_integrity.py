import pytest
from sqlalchemy import select

from app.models.client import Client
from app.models.commercial_governance_federation import CommercialGovernanceFederationPeer
from app.models.commercial_model_supply_chain import CommercialModelIntegrityEvent
from app.models.inference_backend import InferenceBackend
from app.models.model_backend_route import ModelBackendRoute
from app.models.model_registry import ModelRegistry
from app.services.model_policy import resolve_requested_model
from app.services.models.runtime_integrity_monitor import scan_registered_models, summarize_integrity_status
from app.services.models.signed_model_registry import register_model_manifest


def _build_runtime_model(path: str, *, alias: str = "runtime-model", model_id: str = "runtime/model") -> ModelRegistry:
    model = ModelRegistry(
        model_id=model_id,
        model_alias=alias,
        provider="llama.cpp",
        model_file=path,
        context_length=4096,
        is_active=True,
        is_default=True,
        status="configured",
    )
    backend = InferenceBackend(
        name="runtime-local",
        provider="llama.cpp",
        backend_url="http://local",
        is_active=True,
        status="healthy",
    )
    model.backend_routes = [ModelBackendRoute(priority=1, weight=100, state="healthy", inference_backend=backend)]
    return model


@pytest.mark.asyncio
async def test_runtime_integrity_checksum_verified(session, tmp_path):
    model_file = tmp_path / "verified.gguf"
    model_file.write_bytes(b"verified")
    model = _build_runtime_model(str(model_file))
    session.add(model)
    await session.flush()
    await register_model_manifest(
        session,
        model_name=model.model_id,
        model_alias=model.model_alias,
        model_file_path=str(model_file),
        model_format="gguf",
    )

    result = await scan_registered_models(session, scan_type="manual")

    assert result["verified"] == 1
    assert result["drift_detected"] == 0


@pytest.mark.asyncio
async def test_runtime_integrity_checksum_mismatch(session, tmp_path, settings):
    settings.commercial_model_integrity_auto_quarantine = False
    model_file = tmp_path / "mismatch.gguf"
    model_file.write_bytes(b"before")
    model = _build_runtime_model(str(model_file), alias="mismatch-model", model_id="runtime/mismatch")
    session.add(model)
    await session.flush()
    entry = await register_model_manifest(
        session,
        model_name=model.model_id,
        model_alias=model.model_alias,
        model_file_path=str(model_file),
        model_format="gguf",
    )
    model_file.write_bytes(b"after")

    result = await scan_registered_models(session, scan_type="manual")

    assert result["drift_detected"] == 1
    assert entry.trust_state != "quarantined"


@pytest.mark.asyncio
async def test_runtime_integrity_missing_file_creates_alert(session, tmp_path):
    missing_path = tmp_path / "missing.gguf"
    model = _build_runtime_model(str(missing_path), alias="missing-model", model_id="runtime/missing")
    session.add(model)
    await session.flush()
    await register_model_manifest(
        session,
        model_name=model.model_id,
        model_alias=model.model_alias,
        model_file_path=str(missing_path),
        model_format="gguf",
        checksum_sha256="missing-file-checksum",
    )

    result = await scan_registered_models(session, scan_type="manual")

    assert result["missing"] == 1
    events = (await session.execute(select(CommercialModelIntegrityEvent))).scalars().all()
    assert any(item.event_type == "missing_model_detected" for item in events)


@pytest.mark.asyncio
async def test_runtime_integrity_auto_quarantine(session, tmp_path, settings):
    settings.commercial_model_integrity_auto_quarantine = True
    model_file = tmp_path / "quarantine.gguf"
    model_file.write_bytes(b"before")
    model = _build_runtime_model(str(model_file), alias="quarantine-model", model_id="runtime/quarantine")
    session.add(model)
    await session.flush()
    entry = await register_model_manifest(
        session,
        model_name=model.model_id,
        model_alias=model.model_alias,
        model_file_path=str(model_file),
        model_format="gguf",
    )
    model_file.write_bytes(b"after")

    result = await scan_registered_models(session, scan_type="runtime_validation")

    assert result["quarantined"] == 1
    assert entry.trust_state == "quarantined"
    assert model.status == "quarantined"


@pytest.mark.asyncio
async def test_federated_integrity_summary(session):
    session.add(
        CommercialGovernanceFederationPeer(
            peer_cluster_id="peer-integrity",
            environment="production",
            region="us-east",
            status="active",
            sync_mode="manual",
            trust_level="trusted",
        )
    )
    await session.flush()

    summary = await summarize_integrity_status(session)

    assert summary["federated_integrity"]["peer_count"] == 1
    assert summary["federated_integrity"]["peers"][0]["peer_cluster_id"] == "peer-integrity"


@pytest.mark.asyncio
async def test_integrity_payload_sanitized(session, tmp_path):
    model_file = tmp_path / "payload.gguf"
    model_file.write_bytes(b"payload")
    model = _build_runtime_model(str(model_file), alias="payload-model", model_id="runtime/payload")
    session.add(model)
    await session.flush()
    await register_model_manifest(
        session,
        model_name=model.model_id,
        model_alias=model.model_alias,
        model_file_path=str(model_file),
        model_format="gguf",
    )

    await scan_registered_models(session, scan_type="manual")
    summary = await summarize_integrity_status(session)

    rendered = str(summary)
    assert str(model_file) not in rendered
    assert model_file.name not in rendered or "payload.gguf" in rendered


@pytest.mark.asyncio
async def test_enforce_blocks_quarantined(monkeypatch, session, settings):
    settings.commercial_model_supply_chain_enabled = True
    settings.commercial_model_trust_enforcement_mode = "enforce"
    model = _build_runtime_model("/tmp/enforce.gguf", alias="enforce-model", model_id="runtime/enforce")

    async def fake_models(_session):
        return [model]

    monkeypatch.setattr("app.services.model_policy.list_active_registry_models", fake_models)
    entry = await register_model_manifest(session, model_name=model.model_id, model_alias=model.model_alias, model_format="api")
    entry.trust_state = "quarantined"

    with pytest.raises(Exception) as exc:
        await resolve_requested_model(session, client=Client(name="tenant"), requested_model="default")

    assert getattr(exc.value, "status_code", 500) == 403


@pytest.mark.asyncio
async def test_report_only_does_not_block_quarantined(monkeypatch, session, settings):
    settings.commercial_model_supply_chain_enabled = True
    settings.commercial_model_trust_enforcement_mode = "report_only"
    model = _build_runtime_model("/tmp/report.gguf", alias="report-model", model_id="runtime/report")

    async def fake_models(_session):
        return [model]

    monkeypatch.setattr("app.services.model_policy.list_active_registry_models", fake_models)
    entry = await register_model_manifest(session, model_name=model.model_id, model_alias=model.model_alias, model_format="api")
    entry.trust_state = "quarantined"

    selected, requested = await resolve_requested_model(session, client=Client(name="tenant"), requested_model="default")

    assert selected.model_alias == "report-model"
    assert requested == "default"


@pytest.mark.asyncio
async def test_runtime_integrity_endpoints_require_admin_auth(admin_client, admin_token_headers):
    unauthorized = await admin_client.get("/admin/models/integrity/scans")
    assert unauthorized.status_code == 401

    authorized = await admin_client.get("/admin/models/integrity/scans", headers=admin_token_headers)
    assert authorized.status_code == 200
