from app.utils.openai_response import normalize_chat_completion, normalize_chat_stream_line


def test_normalize_chat_completion_strips_reasoning_by_default():
    payload = {
        "id": "chatcmpl-1",
        "object": "chat.completion",
        "created": 1,
        "model": "local-model",
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": "ok",
                    "reasoning_content": "hidden",
                },
            }
        ],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }

    normalized = normalize_chat_completion(payload, include_reasoning=False)

    assert normalized["choices"][0]["message"] == {"role": "assistant", "content": "ok"}


def test_normalize_chat_stream_line_keeps_reasoning_when_requested():
    line = (
        'data: {"id":"chatcmpl-1","object":"chat.completion.chunk","created":1,"model":"local-model",'
        '"choices":[{"index":0,"finish_reason":null,"delta":{"reasoning_content":"step"}}]}'
    )

    normalized = normalize_chat_stream_line(line, include_reasoning=True)

    assert "reasoning_content" in normalized


def test_normalize_chat_stream_line_drops_reasoning_only_delta_by_default():
    line = (
        'data: {"id":"chatcmpl-1","object":"chat.completion.chunk","created":1,"model":"local-model",'
        '"choices":[{"index":0,"finish_reason":null,"delta":{"reasoning_content":"step"}}]}'
    )

    assert normalize_chat_stream_line(line, include_reasoning=False) is None


def test_normalize_chat_completion_strips_qwen_think_blocks_by_default():
    payload = {
        "id": "chatcmpl-1",
        "object": "chat.completion",
        "created": 1,
        "model": "bonsai",
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": "<think>hidden chain</think>\nResposta final",
                },
            }
        ],
    }

    normalized = normalize_chat_completion(payload, include_reasoning=False, prompt_template="qwen")

    assert normalized["choices"][0]["message"]["content"] == "Resposta final"
