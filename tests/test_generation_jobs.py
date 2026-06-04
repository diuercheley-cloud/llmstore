import uuid
from datetime import datetime, timezone

from app.models.generation_job import GenerationJob
from app.services.generation_jobs import serialize_job


def test_serialize_job_preserves_cancelled_state_and_backend_errors():
    job_id = uuid.uuid4()
    client_id = uuid.uuid4()
    now = datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc)
    job = GenerationJob(
        id=job_id,
        client_id=client_id,
        endpoint="/v1/chat/completions/async",
        requested_model="gemma",
        resolved_model="unsloth/gemma-4-E4B-it-GGUF",
        status="cancelled",
        request_json='{"model":"gemma"}',
        backend_errors_json='[{"backend_name":"gemma-local","error":"busy"}]',
        prompt_tokens_estimated=12,
        completion_tokens_estimated=0,
        estimated_cost_usd=0.001,
        max_tokens_requested=64,
        queued_at=now,
        cancelled_at=now,
        created_at=now,
        updated_at=now,
    )

    payload = serialize_job(job)

    assert payload["id"] == str(job_id)
    assert payload["status"] == "cancelled"
    assert payload["backend_errors"][0]["backend_name"] == "gemma-local"
    assert payload["cancelled_at"] == now.isoformat()
    assert payload["response"] is None
    assert payload["attempts"] is None
