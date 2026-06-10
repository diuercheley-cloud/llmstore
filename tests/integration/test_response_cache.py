from app.services.response_cache import build_chat_cache_key, build_completion_cache_key


def test_chat_cache_key_is_stable_for_same_payload():
    first = build_chat_cache_key(
        model="gemma",
        messages=[{"role": "user", "content": "ola"}],
        temperature=0.7,
        top_p=0.95,
        max_tokens=128,
        include_reasoning=False,
    )
    second = build_chat_cache_key(
        model="gemma",
        messages=[{"role": "user", "content": "ola"}],
        temperature=0.7,
        top_p=0.95,
        max_tokens=128,
        include_reasoning=False,
    )

    assert first == second


def test_chat_cache_key_changes_when_reasoning_flag_changes():
    without_reasoning = build_chat_cache_key(
        model="gemma",
        messages=[{"role": "user", "content": "ola"}],
        temperature=0.7,
        top_p=0.95,
        max_tokens=128,
        include_reasoning=False,
    )
    with_reasoning = build_chat_cache_key(
        model="gemma",
        messages=[{"role": "user", "content": "ola"}],
        temperature=0.7,
        top_p=0.95,
        max_tokens=128,
        include_reasoning=True,
    )

    assert without_reasoning != with_reasoning


def test_chat_cache_key_changes_when_schema_version_changes_shape():
    key, _ = build_chat_cache_key(
        model="gemma",
        messages=[{"role": "user", "content": "ola"}],
        temperature=0.7,
        top_p=0.95,
        max_tokens=128,
        include_reasoning=False,
    )

    assert key


def test_completion_cache_key_changes_with_prompt():
    first = build_completion_cache_key(
        model="gemma",
        prompt="primeiro prompt",
        temperature=0.7,
        top_p=0.95,
        max_tokens=128,
    )
    second = build_completion_cache_key(
        model="gemma",
        prompt="segundo prompt",
        temperature=0.7,
        top_p=0.95,
        max_tokens=128,
    )

    assert first != second
