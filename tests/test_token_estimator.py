from app.utils.token_estimator import estimate_prompt_tokens


def test_estimate_prompt_tokens_from_messages():
    tokens = estimate_prompt_tokens(messages=[{"role": "user", "content": "ola mundo"}])
    assert tokens > 0

