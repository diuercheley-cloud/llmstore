"""Python helper library for real provider validation.

Matches real-provider-env.sh functionality for use in Python tests.
Never prints full API keys. Never exposes secrets.
"""

import os
import re
from pathlib import Path


def load_real_provider_env(env_path: Path | str | None = None) -> bool:
    """Load .env.local into os.environ. Returns True if loaded."""
    if env_path is None:
        env_path = Path(__file__).resolve().parents[2] / ".env.local"
    env_path = Path(env_path)
    if not env_path.exists():
        return False
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())
    return True


def is_real_provider_validation_enabled() -> bool:
    val = os.environ.get("REAL_PROVIDER_VALIDATION_ENABLED", "false")
    return val.lower() in ("true", "1")


def mask_provider_key(key: str) -> str:
    if len(key) <= 8:
        return "********"
    return key[:4] + "****" + key[-4:]


def require_provider_key_if_enabled(
    provider_name: str,
    enabled_var: str,
    key_var: str,
) -> tuple[bool, str]:
    enabled = os.environ.get(enabled_var, "false").lower() in ("true", "1")
    key = os.environ.get(key_var, "")
    if enabled and not key:
        return False, f"{provider_name} enabled but {key_var} is empty"
    if enabled and key:
        return True, f"{provider_name} ready, key {mask_provider_key(key)}"
    return True, f"{provider_name} not enabled (SKIP)"


def get_real_provider_max_cost_brl() -> float:
    val = os.environ.get("REAL_PROVIDER_MAX_COST_BRL", "2.00")
    try:
        return float(val)
    except (ValueError, TypeError):
        return 2.00


SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9][a-zA-Z0-9._-]{20,}"),
    re.compile(r"OPENAI_API_KEY=[^\\s]"),
    re.compile(r"DEEPSEEK_API_KEY=[^\\s]"),
    re.compile(r"ANTHROPIC_API_KEY=[^\\s]"),
]


def assert_no_provider_key_leak(
    scan_path: str | Path,
    exclude_pattern: str | None = None,
) -> list[tuple[Path, int, str]]:
    findings = []
    scan_path = Path(scan_path)
    if not scan_path.exists():
        return findings
    files = list(scan_path.rglob("*")) if scan_path.is_dir() else [scan_path]
    for f in files:
        if not f.is_file():
            continue
        if f.suffix in (".pyc", ".pyo", ".gguf", ".bin", ".db", ".sqlite"):
            continue
        try:
            for i, line in enumerate(f.read_text(errors="ignore").split("\n"), 1):
                if exclude_pattern and re.search(exclude_pattern, str(f)):
                    continue
                for pat in SECRET_PATTERNS:
                    if pat.search(line):
                        findings.append((f, i, line.strip()[:80]))
        except Exception:
            continue
    return findings
