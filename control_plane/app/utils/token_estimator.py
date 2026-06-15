def estimate_tokens_from_text(text: str) -> int:
    if not text:
        return 0
    return max(1, int(len(text.split()) * 1.3))


def estimate_prompt_tokens(messages: list[dict] | None = None, prompt: str | None = None) -> int:
    if prompt is not None:
        return estimate_tokens_from_text(prompt)
    if not messages:
        return 0
    total = 0
    for message in messages:
        total += estimate_tokens_from_text(str(message.get("content", ""))) + 4
    return total
