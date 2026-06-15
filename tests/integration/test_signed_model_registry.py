import uuid

import pytest
from app.models.core.client import Client
from app.services.models.model_provenance import create_provenance_attestation
from app.services.models.signed_model_registry import (
    approve_model,
    get_model_trust_state,
    list_trusted_models,
    register_model_manifest,
    revoke_model,
    verify_model_checksum,
)


@pytest.mark.asyncio
async def test_register_local_model_checksum(session, tmp_path, settings):
    settings.commercial_model_require_checksum_for_local = True
    model_file = tmp_path / "demo.gguf"
    model_file.write_bytes(b"gguf-demo")

    entry = await register_model_manifest(
        session,
        model_name="demo/model",
        model_alias="demo",
        provider="llama.cpp",
        model_file_path=str(model_file),
        model_format="gguf",
    )

    assert entry.checksum_sha256
    assert entry.manifest_hash
    assert entry.trust_state == "untrusted"


@pytest.mark.asyncio
async def test_verify_checksum_ok(session, tmp_path):
    model_file = tmp_path / "ok.gguf"
    model_file.write_bytes(b"ok")
    entry = await register_model_manifest(
        session,
        model_name="ok/model",
        model_file_path=str(model_file),
        model_format="gguf",
    )

    result = await verify_model_checksum(session, entry)

    assert result["verified"] is True
    assert result["reason"] == "checksum_ok"


@pytest.mark.asyncio
async def test_checksum_mismatch_quarantines(session, tmp_path, settings):
    settings.commercial_model_quarantine_on_checksum_mismatch = True
    model_file = tmp_path / "bad.gguf"
    model_file.write_bytes(b"before")
    entry = await register_model_manifest(
        session,
        model_name="bad/model",
        model_file_path=str(model_file),
        model_format="gguf",
    )
    model_file.write_bytes(b"after")

    result = await verify_model_checksum(session, entry)

    assert result["verified"] is False
    assert entry.trust_state == "quarantined"


@pytest.mark.asyncio
async def test_approve_and_revoke_model(session, tmp_path):
    model_file = tmp_path / "approve.gguf"
    model_file.write_bytes(b"approve")
    entry = await register_model_manifest(
        session,
        model_name="approve/model",
        model_file_path=str(model_file),
        model_format="gguf",
    )

    approved = await approve_model(session, entry.id, approved_by="security-admin")
    revocation = await revoke_model(
        session,
        entry_id=approved.id,
        reason="policy violation",
        revocation_type="policy_violation",
        revoked_by="security-admin",
    )

    assert approved.trust_state == "revoked"
    assert approved.approved_by == "security-admin"
    assert revocation.model_name == "approve/model"


@pytest.mark.asyncio
async def test_api_provider_manifest_without_local_file(session):
    entry = await register_model_manifest(
        session,
        model_name="api/provider-model",
        provider="openai_compatible",
        model_format="api",
    )

    result = await verify_model_checksum(session, entry)

    assert entry.checksum_sha256 == "manifest-only"
    assert result["verified"] is True
    assert result["reason"] == "manifest_only"


@pytest.mark.asyncio
async def test_tenant_scope_and_payload_sanitization(session, tmp_path):
    client_a = Client(name=f"tenant-a-{uuid.uuid4()}")
    client_b = Client(name=f"tenant-b-{uuid.uuid4()}")
    session.add_all([client_a, client_b])
    await session.flush()

    provenance = await create_provenance_attestation(
        session,
        source_type="manual",
        source_uri="file:///safe/model",
        import_method="manual",
        artifact_hash="artifact-1",
        evidence_json={"api_key": "sk-secret", "scanner": "admin-lab"},
    )
    entry = await register_model_manifest(
        session,
        model_name="tenant/model",
        model_alias="tenant-safe",
        model_format="api",
        provenance_id=provenance.id,
        tenant_scope_json={"client_ids": [str(client_a.id)]},
    )
    await approve_model(session, entry.id, approved_by="approver")

    allowed = await list_trusted_models(session, client=client_a)
    denied_state = await get_model_trust_state(session, "tenant-safe", client=client_b)

    assert allowed and allowed[0].id == entry.id
    assert denied_state["allowed"] is False
    assert provenance.evidence_json["api_key"] == "[REDACTED]"


@pytest.mark.asyncio
async def test_supply_chain_endpoints_require_admin_auth(admin_client, admin_token_headers):
    unauthorized = await admin_client.get("/admin/models/supply-chain/registry")
    assert unauthorized.status_code == 401

    authorized = await admin_client.get(
        "/admin/models/supply-chain/registry", headers=admin_token_headers
    )
    assert authorized.status_code == 200
