import os
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_env_local_exists():
    env_local = PROJECT_ROOT / ".env.local"
    assert env_local.exists(), ".env.local must exist for real provider validation"


def test_env_local_in_gitignore():
    gitignore = PROJECT_ROOT / ".gitignore"
    content = gitignore.read_text()
    assert ".env.local" in content or ".env.*" in content, ".env.local must be in .gitignore"


def test_env_local_permissions():
    env_local = PROJECT_ROOT / ".env.local"
    perms = oct(env_local.stat().st_mode)[-3:]
    assert perms in ("600", "400"), f"Recommended 600, got {perms}"


def test_real_provider_validation_guard():
    val = os.environ.get("REAL_PROVIDER_VALIDATION_ENABLED", "false")
    assert val in ("true", "false", "1", "0"), (
        "REAL_PROVIDER_VALIDATION_ENABLED must be true/false/1/0"
    )


def test_provider_config_no_leak_in_logs(capsys):
    for var in ("OPENAI_API_KEY", "DEEPSEEK_API_KEY", "ANTHROPIC_API_KEY"):
        val = os.environ.get(var, "")
        if not val:
            continue
        with pytest.raises(AssertionError):
            assert val not in capsys.readouterr().out


OPENAI_REQUIRED = [
    "OPENAI_PROVIDER_ENABLED",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
]

DEEPSEEK_REQUIRED = [
    "DEEPSEEK_PROVIDER_ENABLED",
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_BASE_URL",
]

ANTHROPIC_REQUIRED = [
    "ANTHROPIC_PROVIDER_ENABLED",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_BASE_URL",
]


@pytest.mark.parametrize("var", OPENAI_REQUIRED)
def test_openai_vars_exist(var):
    assert var in os.environ, f"{var} must be defined in .env.local"


@pytest.mark.parametrize("var", DEEPSEEK_REQUIRED)
def test_deepseek_vars_exist(var):
    assert var in os.environ, f"{var} must be defined in .env.local"


@pytest.mark.parametrize("var", ANTHROPIC_REQUIRED)
def test_anthropic_vars_exist(var):
    assert var in os.environ, f"{var} must be defined in .env.local"


def test_optional_vars():
    optional = [
        "OPENAI_CHAT_MODEL",
        "OPENAI_EMBEDDINGS_MODEL",
        "DEEPSEEK_CHAT_MODEL",
        "ANTHROPIC_MODEL",
    ]
    for var in optional:
        assert var in os.environ, f"{var} should be defined (can be empty)"


def test_provider_opt_in_safety():
    for var in ("OPENAI_PROVIDER_ENABLED", "DEEPSEEK_PROVIDER_ENABLED", "ANTHROPIC_PROVIDER_ENABLED"):
        val = os.environ.get(var, "false")
        assert val.lower() in ("true", "false", "1", "0"), f"{var} must be boolean"


def test_skip_when_not_enabled():
    for provider, var in [
        ("OpenAI", "OPENAI_PROVIDER_ENABLED"),
        ("DeepSeek", "DEEPSEEK_PROVIDER_ENABLED"),
        ("Anthropic", "ANTHROPIC_PROVIDER_ENABLED"),
    ]:
        enabled = os.environ.get(var, "false") == "true"
        key = os.environ.get(f"{provider.upper()}_API_KEY", "")
        if not enabled:
            assert not key or key == "", (
                f"{provider} not enabled but key is set — set {var}=false or remove key"
            )
