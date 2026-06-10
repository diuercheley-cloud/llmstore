
import pytest
import yaml

from scripts.llm_harness.config import HarnessConfig, get_config


def test_config_defaults():
    config = HarnessConfig()
    assert config.code_agent == "default-coder"
    assert config.docker_image == "python:3.12-slim"

def test_config_load_yaml(tmp_path):
    d = tmp_path / "config"
    d.mkdir()
    f = d / ".harness.yaml"
    f.write_text(yaml.dump({"code_agent": "yaml-agent", "max_steps": 20}))
    
    config = HarnessConfig.load_config(str(f))
    assert config.code_agent == "yaml-agent"
    assert config.max_steps == 20

def test_config_load_toml(tmp_path):
    d = tmp_path / "config"
    d.mkdir()
    f = d / "harness.toml"
    f.write_text('code_agent = "toml-agent"\nmax_steps = 30')
    
    config = HarnessConfig.load_config(str(f))
    assert config.code_agent == "toml-agent"
    assert config.max_steps == 30

def test_config_env_override(monkeypatch):
    monkeypatch.setenv("LLM_HARNESS_CODE_AGENT", "env-agent")
    config = HarnessConfig()
    assert config.code_agent == "env-agent"

def test_config_cli_precedence(tmp_path, monkeypatch):
    # 1. File
    f = tmp_path / ".harness.yaml"
    f.write_text(yaml.dump({"code_agent": "file-agent", "max_steps": 10}))
    
    # 2. Env
    monkeypatch.setenv("LLM_HARNESS_CODE_AGENT", "env-agent")
    monkeypatch.setenv("LLM_HARNESS_MAX_STEPS", "20")
    
    # 3. CLI
    monkeypatch.chdir(tmp_path)
    cli_args = {"code_agent": "cli-agent"}
    
    config = get_config(cli_args)
    
    assert config.code_agent == "cli-agent" # CLI wins over all
    assert config.max_steps == 20           # Env wins over file
    assert config.model == ""               # Default remains empty until configured


def test_config_invalid_yaml(tmp_path):
    from scripts.llm_harness.config import HarnessConfigParseError
    f = tmp_path / ".harness.yaml"
    f.write_text("invalid: yaml: :")
    with pytest.raises(HarnessConfigParseError):
        HarnessConfig.load_config(str(f))


def test_config_invalid_toml(tmp_path):
    from scripts.llm_harness.config import HarnessConfigParseError
    f = tmp_path / "harness.toml"
    f.write_text("invalid toml syntax...")
    with pytest.raises(HarnessConfigParseError):
        HarnessConfig.load_config(str(f))


def test_config_missing_discovery(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = HarnessConfig.load_config()
    assert config.code_agent == "default-coder"



def test_config_explicit_missing_fails():
    from scripts.llm_harness.config import HarnessConfigError
    with pytest.raises(HarnessConfigError, match="Config file not found"):
        HarnessConfig.load_config("nonexistent_config_file.yaml")


def test_config_schema_invalid(tmp_path):
    from scripts.llm_harness.config import HarnessConfigSchemaError
    f = tmp_path / ".harness.yaml"
    f.write_text("max_steps: invalid-type-string")
    with pytest.raises(HarnessConfigSchemaError):
        HarnessConfig.load_config(str(f))


def test_cli_exits_on_invalid_config(tmp_path):
    from unittest.mock import patch

    from scripts.llm_harness.cli import main
    f = tmp_path / ".harness.yaml"
    f.write_text("invalid: yaml: :")
    with patch("sys.argv", ["cli.py", "--config", str(f), "health", "--local-only"]):
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 1


def test_config_new_defaults():
    config = HarnessConfig()
    assert config.workspace_mount_path == "/workspace"
    assert config.temp_base_dir is None
    assert config.loop_timeout == 300
    assert config.max_output_chars == 10000
    assert config.report_output_path == "artifacts/llm_harness"


def test_config_new_defaults_env_override(monkeypatch):
    monkeypatch.setenv("LLM_HARNESS_WORKSPACE_MOUNT_PATH", "/custom/mount")
    monkeypatch.setenv("LLM_HARNESS_TEMP_BASE_DIR", "/custom/temp")
    monkeypatch.setenv("LLM_HARNESS_LOOP_TIMEOUT", "150")
    monkeypatch.setenv("LLM_HARNESS_MAX_OUTPUT_CHARS", "5000")
    monkeypatch.setenv("LLM_HARNESS_REPORT_OUTPUT_PATH", "custom/reports")

    config = HarnessConfig()
    assert config.workspace_mount_path == "/custom/mount"
    assert config.temp_base_dir == "/custom/temp"
    assert config.loop_timeout == 150
    assert config.max_output_chars == 5000
    assert config.report_output_path == "custom/reports"


def test_config_new_defaults_cli_precedence(tmp_path, monkeypatch):
    # 1. File
    f = tmp_path / ".harness.yaml"
    f.write_text(
        yaml.dump(
            {
                "workspace_mount_path": "/file/mount",
                "loop_timeout": 100,
            }
        )
    )

    # 2. Env
    monkeypatch.setenv("LLM_HARNESS_WORKSPACE_MOUNT_PATH", "/env/mount")
    monkeypatch.setenv("LLM_HARNESS_LOOP_TIMEOUT", "200")

    # 3. CLI
    monkeypatch.chdir(tmp_path)
    cli_args = {
        "workspace_mount_path": "/cli/mount",
    }
    config = get_config(cli_args)
    assert config.workspace_mount_path == "/cli/mount"  # CLI wins over all
    assert config.loop_timeout == 200  # Env wins over file
    assert config.report_output_path == "artifacts/llm_harness"  # Defaults

