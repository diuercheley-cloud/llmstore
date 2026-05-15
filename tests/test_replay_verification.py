import pytest
from sqlalchemy import select

from app.models.commercial_inference_reproducibility import CommercialInferenceReproducibilityRecord
from app.services.inference.replay_verification import verify_replay
from app.services.inference.reproducibility import capture_reproducibility_record


@pytest.mark.asyncio
async def test_exact_replay_match(session, settings):
    settings.commercial_replay_capture_prompt_hash_only = False
    record = await capture_reproducibility_record(
        session,
        request_id="req-1",
        correlation_id="corr-1",
        client_id="client-1",
        model_name="demo/model",
        model_alias="demo",
        provider="llama.cpp",
        backend_name="backend-a",
        request_payload={"messages": [{"role": "user", "content": "hello world"}], "temperature": 0.2},
        response_payload={"choices": [{"message": {"content": "exact replay output"}}]},
        prompt_template="chatml",
        metadata_json={"replay_candidate_output": "exact replay output"},
    )
    await session.commit()

    result = await verify_replay(session, record=record, replay_type="exact")
    await session.commit()

    refreshed = await session.get(CommercialInferenceReproducibilityRecord, record.id)
    assert result["replay_result"] == "matched"
    assert refreshed.replay_status == "replayed"
    assert refreshed.replay_similarity == 1.0


@pytest.mark.asyncio
async def test_partial_replay_match(session, settings):
    settings.commercial_replay_capture_prompt_hash_only = False
    record = await capture_reproducibility_record(
        session,
        request_id="req-2",
        correlation_id="corr-2",
        client_id="client-2",
        model_name="demo/model",
        provider="llama.cpp",
        backend_name="backend-a",
        request_payload={"messages": [{"role": "user", "content": "hello brave new world"}]},
        response_payload={"choices": [{"message": {"content": "hello brave new world"}}]},
        metadata_json={"replay_candidate_output": "hello brave old world"},
    )
    await session.commit()

    result = await verify_replay(session, record=record, replay_type="best_effort")
    assert result["replay_result"] == "partial_match"
    assert result["similarity"] < 1.0
    assert result["similarity"] >= 0.85


@pytest.mark.asyncio
async def test_drift_detection_flags_tokenizer_and_runtime(session, settings):
    settings.commercial_replay_capture_prompt_hash_only = False
    record = await capture_reproducibility_record(
        session,
        request_id="req-3",
        correlation_id="corr-3",
        client_id="client-3",
        model_name="demo/model",
        provider="llama.cpp",
        backend_name="backend-a",
        request_payload={"messages": [{"role": "user", "content": "drift me"}]},
        response_payload={"choices": [{"message": {"content": "stable output"}}]},
        tokenizer_name="tok-a",
        tokenizer_version="1",
        runtime_engine="llama.cpp",
        runtime_engine_version="1.0",
        metadata_json={
            "replay_candidate_output": "stable output",
            "replay_runtime_snapshot": {
                "backend_name": "backend-b",
                "runtime_engine": "vllm",
                "runtime_engine_version": "2.0",
                "model_name": "demo/model",
                "model_manifest_hash": "other",
                "runtime_config_json": {"quantization": "Q8_0"},
                "tokenizer_info_json": {"tokenizer_name": "tok-b", "tokenizer_version": "2", "template_hash": "different"},
                "snapshot_hash": "different",
            },
        },
    )
    await session.commit()

    result = await verify_replay(session, record=record, replay_type="cross_backend")
    await session.commit()

    refreshed = await session.get(CommercialInferenceReproducibilityRecord, record.id)
    assert refreshed.replay_status == "drift_detected"
    assert result["drift_report"]["tokenizer_drift"] is True
    assert result["drift_report"]["runtime_drift"] is True
    assert result["drift_report"]["quantization_drift"] is True


@pytest.mark.asyncio
async def test_replay_disabled_returns_failed(session):
    record = await capture_reproducibility_record(
        session,
        request_id="req-4",
        correlation_id="corr-4",
        client_id="client-4",
        model_name="demo/model",
        provider="unknown-provider",
        backend_name="backend-x",
        request_payload={"messages": [{"role": "user", "content": "cannot replay"}], "temperature": 0.9},
        response_payload=None,
    )
    await session.commit()

    result = await verify_replay(session, record=record, replay_type="best_effort")
    assert result["replay_result"] == "failed"
