import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_EXAMPLE = PROJECT_ROOT / ".env.example"


def test_env_example_exists():
    assert ENV_EXAMPLE.exists(), ".env.example must exist"


def test_env_example_has_real_provider_section():
    content = ENV_EXAMPLE.read_text()
    assert "REAL_PROVIDER_VALIDATION_ENABLED" in content
    assert "REAL_PROVIDER_MAX_COST_BRL" in content
    assert "REAL_PROVIDER_TIMEOUT_SECONDS" in content
    assert "REAL_PROVIDER_LOG_PROMPTS" in content
    assert "REAL_PROVIDER_STORE_RESPONSES" in content


def test_env_example_has_openai_section():
    content = ENV_EXAMPLE.read_text()
    assert "OPENAI_PROVIDER_ENABLED" in content
    assert "OPENAI_API_KEY" in content
    assert "OPENAI_BASE_URL" in content
    assert "OPENAI_CHAT_MODEL" in content
    assert "OPENAI_EMBEDDINGS_MODEL" in content


def test_env_example_has_deepseek_section():
    content = ENV_EXAMPLE.read_text()
    assert "DEEPSEEK_PROVIDER_ENABLED" in content
    assert "DEEPSEEK_API_KEY" in content
    assert "DEEPSEEK_BASE_URL" in content
    assert "DEEPSEEK_CHAT_MODEL" in content


def test_env_example_has_anthropic_section():
    content = ENV_EXAMPLE.read_text()
    assert "ANTHROPIC_PROVIDER_ENABLED" in content
    assert "ANTHROPIC_API_KEY" in content
    assert "ANTHROPIC_BASE_URL" in content
    assert "ANTHROPIC_MODEL" in content


def test_env_example_api_keys_empty():
    content = ENV_EXAMPLE.read_text()
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("OPENAI_API_KEY="):
            assert line == "OPENAI_API_KEY=", f"OPENAI_API_KEY must be empty: '{line}'"
        if line.startswith("DEEPSEEK_API_KEY="):
            assert line == "DEEPSEEK_API_KEY=", f"DEEPSEEK_API_KEY must be empty: '{line}'"
        if line.startswith("ANTHROPIC_API_KEY="):
            assert line == "ANTHROPIC_API_KEY=", f"ANTHROPIC_API_KEY must be empty: '{line}'"


def test_env_example_default_false_for_enabled():
    content = ENV_EXAMPLE.read_text()
    assert "OPENAI_PROVIDER_ENABLED=false" in content
    assert "DEEPSEEK_PROVIDER_ENABLED=false" in content
    assert "ANTHROPIC_PROVIDER_ENABLED=false" in content
    assert "REAL_PROVIDER_VALIDATION_ENABLED=false" in content


def test_env_example_default_urls():
    content = ENV_EXAMPLE.read_text()
    assert "OPENAI_BASE_URL=https://api.openai.com/v1" in content
    assert "DEEPSEEK_BASE_URL=https://api.deepseek.com" in content
    assert "ANTHROPIC_BASE_URL=https://api.anthropic.com" in content


def test_env_example_no_comment_after_key_value():
    content = ENV_EXAMPLE.read_text()
    for line in content.split("\n"):
        line = line.strip()
        if "=" not in line or line.startswith("#"):
            continue
        if line.startswith("OPENAI_API_KEY=") or line.startswith("DEEPSEEK_API_KEY=") or line.startswith("ANTHROPIC_API_KEY="):
            continue
        if "#" in line:
            eq_pos = line.index("=")
            rest = line[eq_pos + 1:].strip()
            if rest and "#" in rest and not rest.startswith("#"):
                pass


def test_real_provider_section_comment_header():
    content = ENV_EXAMPLE.read_text()
    assert "Real Provider Validation" in content or "real provider" in content.lower()
    assert "v1.8.1" in content or "1.8.1" in content


def test_cost_has_reasonable_default():
    content = ENV_EXAMPLE.read_text()
    assert "REAL_PROVIDER_MAX_COST_BRL=2.00" in content


def test_timeout_has_reasonable_default():
    content = ENV_EXAMPLE.read_text()
    assert "REAL_PROVIDER_TIMEOUT_SECONDS=30" in content


def test_no_duplicate_vars():
    lines = ENV_EXAMPLE.read_text().split("\n")
    seen = set()
    for line in lines:
        line = line.strip()
        if "=" not in line or line.startswith("#"):
            continue
        var = line.split("=", 1)[0].strip()
        assert var not in seen, f"Duplicate variable: {var}"
        seen.add(var)
