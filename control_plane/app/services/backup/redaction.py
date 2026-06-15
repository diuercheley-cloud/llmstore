from pathlib import Path
from typing import Any

ALLOWLIST = {
    "PORT",
    "HOST",
    "OPERATIONAL_PROFILE",
    "PLATFORM_PROFILE",
    "LOG_LEVEL",
    "DEBUG",
    "ENV",
}

SENSITIVE_KEYWORDS = {
    "token",
    "secret",
    "password",
    "key",
    "credential",
}


class ConfigRedactor:
    def __init__(self):
        self.redacted_keys: list[str] = []
        self.excluded_files: list[str] = []

    def _should_redact(self, key: str) -> bool:
        key_lower = key.lower()
        if key_lower in {k.lower() for k in ALLOWLIST}:
            return False
        return any(kw in key_lower for kw in SENSITIVE_KEYWORDS)

    def redact_dict(self, d: dict[str, Any]) -> dict[str, Any]:
        new_dict = {}
        for k, v in d.items():
            if isinstance(k, str) and self._should_redact(k):
                new_dict[k] = "REDACTED"
                self.redacted_keys.append(k)
            elif isinstance(v, dict):
                new_dict[k] = self.redact_dict(v)
            elif isinstance(v, list):
                new_dict[k] = [self._redact_value(item) for item in v]
            else:
                new_dict[k] = v
        return new_dict

    def _redact_value(self, val: Any) -> Any:
        if isinstance(val, dict):
            return self.redact_dict(val)
        if isinstance(val, list):
            return [self._redact_value(item) for item in val]
        return val

    def redact_env_content(self, content: str) -> str:
        lines = []
        for line in content.splitlines():
            if "=" in line and not line.strip().startswith("#"):
                key, val = line.split("=", 1)
                key_strip = key.strip()
                if self._should_redact(key_strip):
                    lines.append(f"{key_strip}=REDACTED")
                    self.redacted_keys.append(key_strip)
                else:
                    lines.append(line)
            else:
                lines.append(line)
        return "\n".join(lines)

    def redact_file_content(self, path: Path, content: str) -> str:
        import yaml

        if path.suffix in (".yaml", ".yml"):
            try:
                parsed = yaml.safe_load(content)
                if isinstance(parsed, dict):
                    redacted = self.redact_dict(parsed)
                    return yaml.safe_dump(redacted, default_flow_style=False)
            except Exception:
                pass
        return self.redact_env_content(content)

    def get_redacted_keys(self) -> list[str]:
        return list(set(self.redacted_keys))
