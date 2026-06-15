import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9][a-zA-Z0-9._-]{20,}"),
    re.compile(r"sk-ant-[a-zA-Z0-9][a-zA-Z0-9._-]{20,}"),
    re.compile(r"sk-proj-[a-zA-Z0-9][a-zA-Z0-9._-]{20,}"),
]

SAFE_PATTERNS = [
    "sk-example",
    "sk-local-example",
    "sk-demo",
    "sk-****masked",
    "sk-p****abcd",
    "sk-********",
    "YOUR_OPENAI_API_KEY",
    "YOUR_DEEPSEEK_API_KEY",
    "YOUR_ANTHROPIC_API_KEY",
    "sk-",
    "sk-proj-",
    "sk-ant-",
]


def _is_safe_line(line: str) -> bool:
    for safe in SAFE_PATTERNS:
        if safe in line:
            return True
    return False


def _scan_file_for_secrets(filepath: Path) -> list:
    findings = []
    if not filepath.exists():
        return findings
    try:
        content = filepath.read_text(errors="ignore")
    except Exception:
        return findings
    for lineno, line in enumerate(content.split("\n"), 1):
        if _is_safe_line(line):
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(line):
                findings.append((filepath, lineno, line.strip()[:80]))
    return findings


def test_no_real_keys_in_env_example():
    env_example = PROJECT_ROOT / ".env.example"
    findings = _scan_file_for_secrets(env_example)
    assert not findings, "Real-looking keys in .env.example:\n" + "\n".join(
        f"  {f[0]}:{f[1]} {f[2]}" for f in findings
    )


def test_no_real_keys_in_versioned_files():
    versioned_dirs = [
        "scripts",
        "tests",
        "docs",
        "config",
    ]
    findings = []
    for d in versioned_dirs:
        dirpath = PROJECT_ROOT / d
        if not dirpath.exists():
            continue
        for f in sorted(dirpath.rglob("*")):
            if not f.is_file():
                continue
            if f.suffix in (".pyc", ".pyo", ".gguf", ".bin", ".db", ".sqlite"):
                continue
            if ".venv" in str(f) or "__pycache__" in str(f):
                continue
            if f.name == ".env.local" or ".env.local" in str(f):
                continue
            if f.name.startswith(".") and f.suffix == "":
                continue
            findings.extend(_scan_file_for_secrets(f))
    assert not findings, "Real-looking keys in versioned files:\n" + "\n".join(
        f"  {f[0]}:{f[1]} {f[2]}" for f in findings[:20]
    )


def test_api_key_var_names_exist_in_env_example():
    env_example = PROJECT_ROOT / ".env.example"
    content = env_example.read_text()
    expected_vars = [
        "OPENAI_API_KEY=",
        "DEEPSEEK_API_KEY=",
        "ANTHROPIC_API_KEY=",
        "OPENAI_PROVIDER_ENABLED=",
        "DEEPSEEK_PROVIDER_ENABLED=",
        "ANTHROPIC_PROVIDER_ENABLED=",
        "REAL_PROVIDER_VALIDATION_ENABLED=",
        "REAL_PROVIDER_MAX_COST_BRL=",
    ]
    for var in expected_vars:
        assert var in content, f"Missing {var} in .env.example"


def test_env_example_keys_are_empty():
    env_example = PROJECT_ROOT / ".env.example"
    content = env_example.read_text()
    key_vars = ["OPENAI_API_KEY=", "DEEPSEEK_API_KEY=", "ANTHROPIC_API_KEY="]
    for line in content.split("\n"):
        for var in key_vars:
            if line.startswith(var):
                value = line[len(var) :].strip()
                assert value == "", f"{var} in .env.example must be empty, got: '{value}'"


def test_mask_provider_key_masks_middle():
    from scripts.lib.real_provider_env import mask_provider_key

    key = "sk-proj-abcdefghijklmnopqrstuvwxyz123456"
    masked = mask_provider_key(key)
    assert masked.startswith("sk-p")
    assert masked.endswith("3456")
    assert "abcdefghijklmnopqrstuvwxyz123" not in masked
    assert "****" in masked


def test_mask_provider_key_short():
    from scripts.lib.real_provider_env import mask_provider_key

    assert mask_provider_key("abc") == "********"


def test_mask_provider_key_empty():
    from scripts.lib.real_provider_env import mask_provider_key

    assert mask_provider_key("") == "********"
