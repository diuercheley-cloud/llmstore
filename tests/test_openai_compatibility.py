import pytest
from fastapi import HTTPException
from app.utils.validation import normalize_messages, validate_params
from app.schemas.inference import ChatCompletionRequest, ChatMessage
from app.models.client import Client
from app.models.billing_plan import BillingPlan

def test_normalize_messages_string():
    messages = [{"role": "user", "content": "hello"}]
    normalized = normalize_messages(messages)
    assert normalized[0]["content"] == "hello"

def test_normalize_messages_array():
    messages = [{
        "role": "user", 
        "content": [
            {"type": "text", "text": "oi"},
            {"type": "text", "text": "tudo bem?"}
        ]
    }]
    normalized = normalize_messages(messages)
    assert normalized[0]["content"] == "oi\ntudo bem?"

def test_normalize_messages_image_url_fails():
    messages = [{
        "role": "user", 
        "content": [
            {"type": "text", "text": "oi"},
            {"type": "image_url", "image_url": {"url": "http://example.com/img.png"}}
        ]
    }]
    with pytest.raises(HTTPException) as excinfo:
        normalize_messages(messages)
    assert excinfo.value.status_code == 422
    assert "image_url is not supported" in excinfo.value.detail

def test_validate_params_rejects_max_tokens_above_limit():
    plan = BillingPlan(max_output_tokens=1000)
    client = Client(billing_plan=plan)
    
    class MockPayload:
        max_tokens = 32000
        temperature = 0.7
        top_p = 0.9
        stream = False
        
    payload = MockPayload()

    max_tokens, temperature, top_p, effective_plan = validate_params(client, payload)

    assert max_tokens == 1000

def test_pydantic_accepts_high_max_tokens():
    # This just validates the schema changes
    req = ChatCompletionRequest(
        model="gemma",
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=32000
    )
    assert req.max_tokens == 32000
