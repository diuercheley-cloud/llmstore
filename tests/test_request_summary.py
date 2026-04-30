from app.utils.request_summary import summarize_chat_request, summarize_completion_request


def test_chat_request_summary_avoids_prompt_text():
    summary = summarize_chat_request(
        [{"role": "user", "content": "segredo absoluto"}],
        include_reasoning=False,
    )
    assert "segredo absoluto" not in summary
    assert "prompt_sha256=" in summary


def test_completion_request_summary_avoids_prompt_text():
    summary = summarize_completion_request("senha super secreta")
    assert "senha super secreta" not in summary
    assert "prompt_sha256=" in summary
