from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scripts.llm_harness.completions import (
    CompletionRequest,
    get_completion_suggestions,
    split_file_at_cursor,
)


def test_split_file_at_cursor():
    content = "line 1\nline 2\nline 3"
    # Split at line 2, column 5 ("line ")
    prefix, suffix = split_file_at_cursor(content, 2, 5)
    assert prefix == "line 1\nline "
    assert suffix == "2\nline 3"

    # Out of bounds lines
    p, s = split_file_at_cursor(content, 5, 0)
    assert p == content
    assert s == ""


@pytest.mark.asyncio
async def test_completions_fake_provider(tmp_path):
    ws_path = tmp_path / "workspace"
    ws_path.mkdir()

    test_file = ws_path / "app.py"
    test_file.write_text("def hello():\n    ")

    request = CompletionRequest(
        file_path=str(test_file),
        cursor_line=2,
        cursor_column=4,
    )

    # Use fake provider
    suggestions = await get_completion_suggestions(
        request=request, workspace_root=str(ws_path), provider_name="fake"
    )

    assert len(suggestions) == 1
    assert suggestions[0].text == "    print('hello world')"
    assert suggestions[0].confidence == 0.95
    assert suggestions[0].explanation == "Autocomplete print statement"

    # Ensure suggestion is NOT applied automatically (file content is unchanged)
    assert test_file.read_text() == "def hello():\n    "


@pytest.mark.asyncio
async def test_completions_file_outside_repository(tmp_path):
    ws_path = tmp_path / "workspace"
    ws_path.mkdir()

    outside_path = tmp_path / "outside.py"
    outside_path.write_text("print('outside')")

    request = CompletionRequest(
        file_path=str(outside_path),
        cursor_line=1,
        cursor_column=5,
    )

    with pytest.raises(PermissionError, match="outside the workspace repository"):
        await get_completion_suggestions(
            request=request, workspace_root=str(ws_path), provider_name="fake"
        )


@pytest.mark.asyncio
@patch("scripts.llm_harness.completions.create_code_agent")
async def test_completions_prompt_and_secrets_redaction(mock_create_agent, tmp_path):
    ws_path = tmp_path / "workspace"
    ws_path.mkdir()

    # File with AWS API key secret in prefix
    test_file = ws_path / "app.py"
    test_file.write_text("key = 'AKIA1234567890123456'\ndef hello():\n    ")

    request = CompletionRequest(
        file_path=str(test_file),
        cursor_line=3,
        cursor_column=4,
    )

    # Mock agent chat completion
    mock_agent = MagicMock()
    mock_agent.chat_completion = AsyncMock(
        return_value={
            "choices": [{"message": {"content": '{"text": "return True", "confidence": 0.9}'}}]
        }
    )
    mock_create_agent.return_value = mock_agent

    suggestions = await get_completion_suggestions(
        request=request, workspace_root=str(ws_path), provider_name="openai-compatible"
    )

    assert len(suggestions) == 1
    assert suggestions[0].text == "return True"
    assert suggestions[0].confidence == 0.9

    # Verify that the FIM prompt has prefix/suffix and that secrets are redacted
    mock_create_agent.assert_called_once()
    args, kwargs = mock_agent.chat_completion.call_args
    prompt_content = args[0][0]["content"]

    assert "PREFIX" in prompt_content
    assert "SUFFIX" in prompt_content
    assert "AKIA1234567890123456" not in prompt_content
    assert "[REDACTED_AWS_KEY]" in prompt_content


@pytest.mark.asyncio
@patch("scripts.llm_harness.indexing.get_retrieved_context")
@patch("scripts.llm_harness.completions.create_code_agent")
async def test_completions_include_retrieved_context(
    mock_create_agent,
    mock_get_retrieved_context,
    tmp_path,
):
    ws_path = tmp_path / "workspace"
    ws_path.mkdir()
    test_file = ws_path / "app.py"
    test_file.write_text("def hello():\n    ")

    mock_get_retrieved_context.return_value = "=== Retrieved Context ===\nhelper docs"
    mock_agent = MagicMock()
    mock_agent.chat_completion = AsyncMock(
        return_value={"choices": [{"message": {"content": '{"text":"pass"}'}}]}
    )
    mock_create_agent.return_value = mock_agent

    request = CompletionRequest(
        file_path=str(test_file),
        cursor_line=2,
        cursor_column=4,
    )
    await get_completion_suggestions(
        request=request,
        workspace_root=str(ws_path),
        provider_name="openai-compatible",
    )

    prompt_content = mock_agent.chat_completion.call_args[0][0][0]["content"]
    assert "## Retrieved Context:" in prompt_content
    assert "helper docs" in prompt_content


@pytest.mark.asyncio
@patch("scripts.llm_harness.completions.create_code_agent")
async def test_completions_retry_on_empty_or_truncated_response(
    mock_create_agent,
    tmp_path,
):
    ws_path = tmp_path / "workspace"
    ws_path.mkdir()
    test_file = ws_path / "app.py"
    test_file.write_text("def hello():\n    return \n")

    first_agent = MagicMock()
    first_agent.chat_completion = AsyncMock(
        return_value={
            "choices": [
                {
                    "message": {"content": ""},
                    "finish_reason": "length",
                }
            ]
        }
    )
    second_agent = MagicMock()
    second_agent.chat_completion = AsyncMock(
        return_value={
            "choices": [
                {
                    "message": {"content": '{"text":"42","confidence":0.9}'},
                    "finish_reason": "stop",
                }
            ]
        }
    )
    mock_create_agent.side_effect = [first_agent, second_agent]

    request = CompletionRequest(
        file_path=str(test_file),
        cursor_line=2,
        cursor_column=11,
    )
    suggestions = await get_completion_suggestions(
        request=request,
        workspace_root=str(ws_path),
        provider_name="openai-compatible",
        config_overrides={"max_tokens": 128},
    )

    assert suggestions[0].text == "42"
    assert mock_create_agent.call_count == 2
    first_cfg = mock_create_agent.call_args_list[0].args[1]
    second_cfg = mock_create_agent.call_args_list[1].args[1]
    assert first_cfg["max_tokens"] == 512
    assert second_cfg["max_tokens"] == 1024
    retry_prompt = second_agent.chat_completion.call_args[0][0][0]["content"]
    assert "## Retrieved Context:" not in retry_prompt
