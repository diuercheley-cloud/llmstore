import json

import pytest
from app.models.commercial.commercial_inference_reproducibility import (
    CommercialInferenceReproducibilityRecord,
    CommercialInferenceRuntimeSnapshot,
)
from app.models.core.client import Client
from app.services.audit import log_request
from sqlalchemy import select


@pytest.mark.asyncio
async def test_reproducibility_capture_creates_record_and_snapshot(session, settings):
    settings.commercial_reproducibility_enabled = True
    settings.commercial_replay_capture_prompt_hash_only = True
    client = Client(name="repro-client", billing_status="active", is_blocked=False)
    session.add(client)
    await session.flush()

    request_payload = {
        "model": "demo/model",
        "messages": [{"role": "user", "content": "hello deterministic world"}],
        "temperature": 0.7,
        "top_p": 0.9,
        "seed": 123,
        "max_tokens": 64,
    }
    response_payload = {
        "id": "chatcmpl-test",
        "choices": [{"message": {"content": "hello deterministic world back"}}],
    }

    await log_request(
        session,
        client_id=client.id,
        model="demo/model",
        endpoint="/v1/chat/completions",
        prompt_tokens=10,
        completion_tokens=8,
        latency_ms=42,
        status_code=200,
        is_stream=False,
        estimated_cost_usd=0.01,
        backend_name="local-backend",
        attempts=1,
        fallback_used=False,
        cache_hit=False,
        request_summary="demo request",
        request_payload=request_payload,
        response_payload=response_payload,
        reproducibility_context={
            "model_alias": "demo",
            "provider": "llama.cpp",
            "prompt_template": "chatml",
            "runtime_engine": "llama.cpp",
            "runtime_engine_version": "1.0.0",
            "model_metadata_json": json.dumps({"model_file": "demo-Q4_K_M.gguf"}),
            "backend_metadata_json": json.dumps({"version": "0.5.1", "tokenizer_version": "v1"}),
        },
    )
    await session.commit()

    record = (await session.execute(select(CommercialInferenceReproducibilityRecord))).scalar_one()
    snapshot = (await session.execute(select(CommercialInferenceRuntimeSnapshot))).scalar_one()

    assert record.request_id is not None
    assert record.seed == 123
    assert record.replay_supported is True
    assert record.prompt_hash
    assert record.request_payload_hash
    assert record.response_payload_hash
    assert record.runtime_config_hash == snapshot.snapshot_hash
    assert "prompt_text" not in (record.metadata_json or {})
    assert "response_text" in (record.metadata_json or {})


@pytest.mark.asyncio
async def test_reproducibility_seed_is_clamped_to_int32(session, settings):
    settings.commercial_reproducibility_enabled = True
    client = Client(name="seed-client", billing_status="active", is_blocked=False)
    session.add(client)
    await session.flush()

    request_payload = {
        "model": "demo/model",
        "messages": [{"role": "user", "content": "seed overflow"}],
        "temperature": 0.2,
        "seed": 4145874907,
    }

    await log_request(
        session,
        client_id=client.id,
        model="demo/model",
        endpoint="/v1/chat/completions",
        prompt_tokens=2,
        completion_tokens=2,
        latency_ms=7,
        status_code=200,
        is_stream=False,
        estimated_cost_usd=0.0,
        backend_name="local-backend",
        attempts=1,
        fallback_used=False,
        cache_hit=False,
        request_summary="seed overflow",
        request_payload=request_payload,
        response_payload={"choices": [{"message": {"content": "ok"}}]},
        reproducibility_context={
            "provider": "llama.cpp",
            "prompt_template": "chatml",
            "runtime_engine": "llama.cpp",
        },
    )
    await session.commit()

    record = (await session.execute(select(CommercialInferenceReproducibilityRecord))).scalar_one()
    assert record.seed == (4145874907 & 0x7FFFFFFF)
    assert 0 <= record.seed <= 0x7FFFFFFF


@pytest.mark.asyncio
async def test_reproducibility_payloads_are_sanitized(session, settings):
    settings.commercial_reproducibility_enabled = True
    client = Client(name="sanitized-client", billing_status="active", is_blocked=False)
    session.add(client)
    await session.flush()

    await log_request(
        session,
        client_id=client.id,
        model="demo/model",
        endpoint="/v1/chat/completions",
        prompt_tokens=1,
        completion_tokens=1,
        latency_ms=5,
        status_code=200,
        is_stream=False,
        estimated_cost_usd=0.0,
        backend_name="safe-backend",
        attempts=1,
        fallback_used=False,
        cache_hit=False,
        request_summary="summary",
        request_payload={"messages": [{"role": "user", "content": "sensitive prompt"}]},
        response_payload={"choices": [{"message": {"content": "safe answer"}}]},
        reproducibility_context={
            "provider": "llama.cpp",
            "metadata_json": {"api_key": "sk-secret", "prompt": "must-redact"},
        },
    )
    await session.commit()

    record = (await session.execute(select(CommercialInferenceReproducibilityRecord))).scalar_one()
    assert record.metadata_json["api_key"] == "[REDACTED]"
    assert record.metadata_json["prompt"] == "[REDACTED]"


@pytest.mark.asyncio
async def test_reproducibility_endpoints_require_admin_auth(admin_client, admin_token_headers):
    unauthorized = await admin_client.get("/admin/inference/reproducibility/status")
    assert unauthorized.status_code == 401

    authorized = await admin_client.get(
        "/admin/inference/reproducibility/status", headers=admin_token_headers
    )
    assert authorized.status_code == 200
