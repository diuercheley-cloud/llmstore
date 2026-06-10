import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from scripts.llm_harness.cli_commands import run_models_command
from scripts.llm_harness.config import get_config

@pytest.mark.asyncio
async def test_run_models_command_list(capsys):
    args = MagicMock()
    args.models_command = "list"
    args.workspace = None
    args.config = None
    with patch("scripts.llm_harness.cli_commands.build_config_overrides", return_value={}), \
         patch("scripts.llm_harness.config.get_config") as mock_get_config:
        
        mock_cfg = MagicMock()
        mock_cfg.models = {
            "default": "local-qwen",
            "profiles": {
                "local-qwen": {
                    "provider": "stub",
                    "model": "qwen"
                }
            },
            "routing": {
                "bugfix": "local-qwen"
            }
        }
        mock_get_config.return_value = mock_cfg
        
        await run_models_command(args)
        captured = capsys.readouterr()
        assert "Model Profiles:" in captured.out
        assert "Profile: local-qwen" in captured.out


@pytest.mark.asyncio
async def test_run_models_command_test_success(capsys):
    args = MagicMock()
    args.models_command = "test"
    args.profile = "local-qwen"
    args.workspace = None
    args.config = None
    
    with patch("scripts.llm_harness.cli_commands.build_config_overrides", return_value={}), \
         patch("scripts.llm_harness.config.get_config") as mock_get_config:
        
        mock_cfg = MagicMock()
        mock_cfg.models = {
            "profiles": {
                "local-qwen": {
                    "provider": "stub",
                    "model": "qwen"
                }
            }
        }
        mock_cfg.allow_cloud_models = True
        mock_get_config.return_value = mock_cfg
        
        mock_agent = MagicMock()
        mock_agent.health_check = AsyncMock(return_value={
            "status": "healthy",
            "details": {
                "selected_model": "qwen",
                "supports_native_tool_calling": False,
                "native_tool_calling_probe": {
                    "status": "no_tool_calls",
                    "reason": "Probe response did not include native tool_calls.",
                },
            },
        })
        mock_agent.chat_completion = AsyncMock(return_value={
            "choices": [{"message": {"content": "pong"}}]
        })
        
        with patch(
            "scripts.llm_harness.providers.create_code_agent",
            return_value=mock_agent
        ):
            await run_models_command(args)
            captured = capsys.readouterr()
            assert "Testing Model Profile: local-qwen" in captured.out
            assert "Selected Model: qwen" in captured.out
            assert "Native Tool Calling: NOT SUPPORTED" in captured.out
            assert "Response: SUCCESS" in captured.out


def test_model_profiles_load_from_harness_yaml(tmp_path, monkeypatch):
    config_file = tmp_path / ".harness.yaml"
    config_file.write_text(
        """
models:
  default: local-qwen
  profiles:
    local-qwen:
      provider: stub
      model: qwen
  routing:
    bugfix: local-qwen
"""
    )
    monkeypatch.chdir(tmp_path)
    config = get_config({})
    assert config.models["default"] == "local-qwen"
    assert config.models["profiles"]["local-qwen"]["model"] == "qwen"
