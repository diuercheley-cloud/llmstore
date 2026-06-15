import pytest
from app.models.core.client import Client
from app.models.core.inference_backend import InferenceBackend
from app.models.core.model_backend_route import ModelBackendRoute
from app.models.core.model_registry import ModelRegistry
from app.services.model_policy import resolve_requested_model
from app.services.models.model_provenance import create_provenance_attestation
from app.services.models.signed_model_registry import approve_model, register_model_manifest
from app.services.security.offline_crl import apply_offline_crl, create_offline_crl
from fastapi import HTTPException


def _build_runtime_model() -> ModelRegistry:
    model = ModelRegistry(
        model_id="supply/model",
        model_alias="supply-model",
        provider="llama.cpp",
        model_file="supply.gguf",
        context_length=4096,
        is_active=True,
        is_default=True,
        status="configured",
    )
    backend = InferenceBackend(
        name="local-backend",
        provider="llama.cpp",
        backend_url="http://local",
        is_active=True,
        status="healthy",
    )
    model.backend_routes = [
        ModelBackendRoute(priority=1, weight=100, state="healthy", inference_backend=backend)
    ]
    return model


@pytest.mark.asyncio
async def test_pending_blocked_in_enforce(monkeypatch, session, settings):
    settings.commercial_model_supply_chain_enabled = True
    settings.commercial_model_trust_enforcement_mode = "enforce"
    model = _build_runtime_model()

    async def fake_models(_session):
        return [model]

    monkeypatch.setattr("app.services.model_policy.list_active_registry_models", fake_models)
    await register_model_manifest(session, model_name="supply-model", model_format="api")

    with pytest.raises(HTTPException) as exc:
        await resolve_requested_model(
            session, client=Client(name="tenant"), requested_model="default"
        )

    assert exc.value.status_code == 403
    assert exc.value.detail["error"] == "model_not_trusted"


@pytest.mark.asyncio
async def test_trusted_allowed_in_enforce(monkeypatch, session, settings):
    settings.commercial_model_supply_chain_enabled = True
    settings.commercial_model_trust_enforcement_mode = "enforce"
    model = _build_runtime_model()

    async def fake_models(_session):
        return [model]

    monkeypatch.setattr("app.services.model_policy.list_active_registry_models", fake_models)
    entry = await register_model_manifest(session, model_name="supply-model", model_format="api")
    await approve_model(session, entry.id, approved_by="ops")

    selected, requested = await resolve_requested_model(
        session, client=Client(name="tenant"), requested_model="default"
    )

    assert selected.model_alias == "supply-model"
    assert requested == "default"


@pytest.mark.asyncio
async def test_report_only_does_not_block(monkeypatch, session, settings):
    settings.commercial_model_supply_chain_enabled = True
    settings.commercial_model_trust_enforcement_mode = "report_only"
    model = _build_runtime_model()

    async def fake_models(_session):
        return [model]

    monkeypatch.setattr("app.services.model_policy.list_active_registry_models", fake_models)
    await register_model_manifest(session, model_name="supply-model", model_format="api")

    selected, _ = await resolve_requested_model(
        session, client=Client(name="tenant"), requested_model="default"
    )

    assert selected.model_alias == "supply-model"


@pytest.mark.asyncio
async def test_crl_revokes_model(session):
    provenance = await create_provenance_attestation(
        session,
        source_type="airgap",
        source_cluster_id="peer-a",
        import_method="airgap",
        artifact_hash="artifact-supply",
        evidence_json={"scanner": "offline"},
    )
    entry = await register_model_manifest(
        session,
        model_name="crl-model",
        model_alias="crl-model",
        model_format="api",
        provenance_id=provenance.id,
    )
    await approve_model(session, entry.id, approved_by="ops")
    crl = await create_offline_crl(
        session,
        crl_version="38.0",
        revoked_bundle_hashes_json=[entry.manifest_hash],
        revoked_peer_ids_json=["peer-a"],
        reason="compromised",
    )

    result = await apply_offline_crl(session, crl.id)

    assert result["revoked_bundles"] >= 1
    assert entry.trust_state == "revoked"
