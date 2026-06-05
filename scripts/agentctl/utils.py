import json
import logging
import os
import re
import sys
from typing import Any, Dict, List, Optional

import yaml

# Redaction patterns for security
SECRET_PATTERNS = [
    re.compile(r"(api[_-]key|secret|password|token|auth|credential|sk-[a-zA-Z0-9]{20,})", re.IGNORECASE),
]

def redact_sensitive_data(data: Any) -> Any:
    """Redacts sensitive information from dictionaries or strings."""
    if isinstance(data, dict):
        return {k: redact_sensitive_data(v) if not any(p.search(k) for p in SECRET_PATTERNS) else "[REDACTED]" for k, v in data.items()}
    elif isinstance(data, list):
        return [redact_sensitive_data(i) for i in data]
    elif isinstance(data, str):
        # Basic redaction for string values that look like keys
        if len(data) > 20 and any(p.search(data) for p in SECRET_PATTERNS):
            return "[REDACTED]"
    return data

def format_output(data: Any, use_json: bool = False):
    """Formats output as JSON or human-readable text."""
    if use_json:
        print(json.dumps(redact_sensitive_data(data), indent=2))
    else:
        if isinstance(data, dict):
            for k, v in redact_sensitive_data(data).items():
                print(f"{k}: {v}")
        elif isinstance(data, list):
            for item in redact_sensitive_data(data):
                print(f"- {item}")
        else:
            print(data)

def load_yaml(path: str) -> Dict[str, Any]:
    """Loads a YAML file with error handling."""
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading {path}: {e}", file=sys.stderr)
        sys.exit(1)

def confirm_action(message: str, force_yes: bool = False) -> bool:
    """Asks for confirmation before proceeding with side effects."""
    if force_yes:
        return True
    ans = input(f"{message} [y/N]: ").lower()
    return ans in ("y", "yes")

class CLIColor:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
