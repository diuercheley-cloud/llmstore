import hashlib
import uuid

import pytest
from app.services.model_provenance.service import ModelProvenanceService, StandardOutputWatermarker


@pytest.mark.asyncio
async def test_model_provenance_verification(session):
    service = ModelProvenanceService(session)

    # 1. Register a model
    weights_content = "model-weights-v1"
    weights_hash = hashlib.sha256(weights_content.encode()).hexdigest()

    record = await service.register_model(
        model_id="llama-3-test",
        source="huggingface://meta-llama/Llama-3",
        license="Llama-3-License",
        weights_hash=weights_hash,
    )
    await session.commit()

    assert record.signature_status == "unverified"

    # 2. Verify provenance
    verified = await service.verify_provenance(str(record.id))
    assert verified.signature_status == "verified"
    assert verified.verified_at is not None


@pytest.mark.asyncio
async def test_output_watermarking_determinism():
    watermarker = StandardOutputWatermarker()
    text = "This is a generated response from the AI."
    model_id = "gpt-4"
    run_id = str(uuid.uuid4())

    res1 = await watermarker.apply_watermark(text, model_id, run_id)
    res2 = await watermarker.apply_watermark(text, model_id, run_id)

    # Should be deterministic for same input
    assert res1["watermark_id"] == res2["watermark_id"]
    assert res1["verification_hash"] == res2["verification_hash"]

    # Different run_id should change watermark_id
    res3 = await watermarker.apply_watermark(text, model_id, str(uuid.uuid4()))
    assert res1["watermark_id"] != res3["watermark_id"]


@pytest.mark.asyncio
async def test_model_provenance_api_flow(admin_client, session, admin_token_headers):
    headers = admin_token_headers
    service = ModelProvenanceService(session)

    record = await service.register_model(
        model_id="api-test-model",
        source="local://models/test",
        weights_hash="invalid-hash",  # Should fail verification
    )
    await session.commit()

    # 1. List
    resp = await admin_client.get("/api/admin/models/provenance", headers=headers)
    assert resp.status_code == 200
    assert any(r["model_id"] == "api-test-model" for r in resp.json())

    # 2. Verify
    resp_v = await admin_client.post(
        f"/api/admin/models/provenance/verify/{record.id}", headers=headers
    )
    assert resp_v.status_code == 200
    assert resp_v.json()["signature_status"] == "failed"  # invalid hash length/type mock


@pytest.mark.asyncio
async def test_model_unverified_by_default(session):
    service = ModelProvenanceService(session)
    record = await service.register_model(model_id="unverified-model", source="test")
    await session.commit()
    assert record.signature_status == "unverified"


@pytest.mark.asyncio
async def test_file_hash_change_affects_verification(session):
    service = ModelProvenanceService(session)
    # Correct hash length (64)
    valid_hash = "a" * 64
    record = await service.register_model(
        model_id="hash-model", source="test", weights_hash=valid_hash
    )
    await session.commit()

    verified = await service.verify_provenance(str(record.id))
    assert verified.signature_status == "verified"

    # Change to invalid hash
    record.weights_hash = "short-hash"
    await session.commit()

    re_verified = await service.verify_provenance(str(record.id))
    assert re_verified.signature_status == "failed"


@pytest.mark.asyncio
async def test_watermark_verify_api(admin_client, admin_token_headers):
    headers = admin_token_headers
    payload = {"text": "Suspicious text to check for watermark"}

    resp = await admin_client.post(
        "/api/admin/models/watermark/verify", json=payload, headers=headers
    )
    assert resp.status_code == 200
    assert "is_authentic" in resp.json()
