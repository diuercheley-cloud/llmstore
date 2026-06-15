import os
import tomllib
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from .defaults import (
    DOCKER_CPU_LIMIT,
    DOCKER_IMAGE,
    DOCKER_MEMORY_LIMIT,
    DOCKER_PIDS_LIMIT,
    MAX_OUTPUT_CHARS,
    MAX_TOKENS,
    REPORT_OUTPUT_PATH,
    TEMP_BASE_DIR,
    TIMEOUT,
    WORKSPACE_MOUNT_PATH,
)


class MCPServerConfig(BaseModel):
    name: str
    command: str
    args: list[str] = Field(default_factory=list)


class MCPConfig(BaseModel):
    enabled: bool = False
    servers: list[MCPServerConfig] = Field(default_factory=list)


class HarnessConfigError(Exception):
    """Base exception for all Harness configuration errors."""

    pass


class HarnessConfigParseError(HarnessConfigError):
    """Raised when the YAML or TOML file has syntax/parsing errors."""

    pass


class HarnessConfigSchemaError(HarnessConfigError):
    """Raised when parsed configuration violates the schema (type mismatch, invalid values)."""

    pass


class HarnessConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LLM_HARNESS_", env_nested_delimiter="__", extra="ignore"
    )

    code_agent: str = "default-coder"
    provider: str = ""
    model: str = ""
    base_url: str = ""
    api_key_env: str = "OPENAI_API_KEY"
    approval_policy: str = "manual"
    sandbox: bool = False
    docker_image: str = DOCKER_IMAGE
    test_command: str = "pytest"
    max_steps: int = 10
    report_format: str = "markdown"
    self_heal: bool = True
    timeout: float = 30.0
    local_model_timeout: float = 300.0
    max_retries: int = 3
    auto_increase_timeout: bool = False
    stream: bool = False
    stream_local_default: bool = True
    verbose_stream: bool = False
    tool_calling: Literal["auto", "native", "json"] = "auto"
    supports_tool_calling: bool = False
    allow_native_tools_for_local: bool = False
    lm_studio_compatibility: bool = True
    capability_cache_ttl_seconds: int = 300
    workspace_mount_path: str = WORKSPACE_MOUNT_PATH
    temp_base_dir: str | None = TEMP_BASE_DIR
    loop_timeout: int = TIMEOUT
    max_output_chars: int = MAX_OUTPUT_CHARS
    report_output_path: str = REPORT_OUTPUT_PATH
    sandbox_network: Literal["none", "host", "proxy"] = "none"
    proxy_url: str | None = None
    docker_memory_limit: str = DOCKER_MEMORY_LIMIT
    docker_cpu_limit: str = DOCKER_CPU_LIMIT
    docker_pids_limit: int = DOCKER_PIDS_LIMIT
    cache: Literal["disabled", "llm", "read-only"] = "disabled"
    cache_dir: str = ".llm_harness_cache"
    pricing_file: str | None = None
    max_cost_per_run: float | None = None
    max_tokens_per_run: int | None = None
    memory: Literal["disabled", "local"] = "local"
    memory_dir: str = ".llm_harness_memory"
    memory_retention_days: int = 30
    agent_mode: Literal["single", "team", "supervisor", "autonomous", "planner-coder-reviewer"] = (
        "single"
    )
    agent_registry_file: str = "config/agent-registry.yaml"
    teams: dict[str, Any] = Field(default_factory=dict)
    default_team: str | None = None
    approval_mode: Literal["auto", "deny", "interactive", "non_interactive"] = "auto"
    approval_default: Literal["allow", "deny"] = "deny"
    edit_action_before_run: bool = False
    checkpoint_dir: str = ".llm_harness_checkpoints"
    checkpoint_every_step: bool = False
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    max_tokens: int | None = MAX_TOKENS
    multimodal: bool = False
    audio_path: str | None = None
    video_path: str | None = None
    auto: bool = False
    max_auto_fixes: int = 3
    stop_on_risk: bool = False
    require_approval_for_edits: bool = False
    models: dict[str, Any] = Field(default_factory=dict)
    model_profile: str | None = None
    fallback_model_profile: str | None = None
    allow_cloud_models: bool = True
    is_reasoning_model: bool = False

    @classmethod
    def _read_file(cls, config_path: str | None = None) -> dict[str, Any]:
        config_data = {}
        paths_to_check: list[str] = []

        if config_path is not None:
            paths_to_check.append(config_path)
        else:
            paths_to_check.extend([".harness.yaml", ".harness.yml", "harness.toml"])

        for path in paths_to_check:
            if config_path is not None and not os.path.exists(path):
                raise HarnessConfigError(f"Config file not found: {path}")

            if os.path.exists(path):
                try:
                    with open(path, "rb") as f:
                        if path.endswith(".toml"):
                            config_data = tomllib.load(f)
                        elif path.endswith((".yaml", ".yml")):
                            config_data = yaml.safe_load(f)
                    break
                except tomllib.TOMLDecodeError as e:
                    raise HarnessConfigParseError(
                        f"Failed to parse TOML config from {path}: {e}"
                    ) from e
                except yaml.YAMLError as e:
                    raise HarnessConfigParseError(
                        f"Failed to parse YAML config from {path}: {e}"
                    ) from e
                except Exception as e:
                    raise HarnessConfigParseError(f"Failed to load config from {path}: {e}") from e

        return config_data or {}

    @classmethod
    def load_config(cls, config_path: str | None = None) -> "HarnessConfig":
        file_data = cls._read_file(config_path)

        # Precedence: Env > File.
        # BaseSettings constructor arguments (kwargs) have higher priority than Env vars.
        # So we only pass file_data if it's NOT in env.
        filtered_file_data = {}
        for k, v in file_data.items():
            env_key = f"LLM_HARNESS_{k.upper()}"
            if env_key not in os.environ:
                filtered_file_data[k] = v

        try:
            return cls(**filtered_file_data)
        except ValidationError as e:
            raise HarnessConfigSchemaError(f"Invalid configuration schema: {e}") from e


def get_config(cli_args: dict[str, Any] | None = None) -> HarnessConfig:
    """
    Returns config with precedence: CLI > Env > Config File > Defaults
    """
    config_path = None
    if cli_args:
        config_path = cli_args.pop("config", None)

    # 1. Load from file and env (Env > File)
    config = HarnessConfig.load_config(config_path)

    # 2. Override with CLI args if provided (CLI > Env)
    if cli_args:
        overrides = {k: v for k, v in cli_args.items() if v is not None}

        config_dict = config.model_dump()
        config_dict.update(overrides)
        try:
            config = HarnessConfig(**config_dict)
        except ValidationError as e:
            raise HarnessConfigSchemaError(
                f"Invalid configuration schema from CLI overrides: {e}"
            ) from e

    return config
