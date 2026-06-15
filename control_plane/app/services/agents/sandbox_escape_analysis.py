"""
Owner: security-ops
Status: implementation
"""

import logging
import re
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Sensitive paths and patterns that should be blocked from tool input
BLOCKED_PATH_PATTERNS = [
    r"\.env(\..+)?",
    r"data/pki",
    r"uploads/rag",
    r"models/.*",
    r"\.ssh/.*",
    r"id_rsa.*",
    r"/proc/.*",
    r"/sys/.*",
    r"docker\.sock",
    r"/var/run/docker\.sock",
    r"\.\./.*",  # Path traversal
]

BLOCKED_IP_PATTERNS = [
    r"169\.254\.169\.254",  # Cloud metadata
    r"127\.0\.0\.1",
    r"localhost",
    r"192\.168\..*",
    r"10\..*",
    r"172\.(1[6-9]|2[0-9]|3[0-1])\..*",
]

# Blocked code patterns (imports, sensitive builtins)
BLOCKED_CODE_PATTERNS = [
    r"import\s+os",
    r"import\s+subprocess",
    r"import\s+sys",
    r"import\s+socket",
    r"import\s+pty",
    r"from\s+os\s+import",
    r"from\s+subprocess\s+import",
    r"__import__",
    r"eval\(",
    r"exec\(",
    r"getattr\(",
    r"setattr\(",
    r"open\(",
    r"subprocess\.",
    r"os\.(system|spawn|popen|exec|fork)",
]


class SandboxEscapeAnalyzer:
    """
    Service for analyzing tool inputs and code for potential sandbox escape attempts.
    """

    def __init__(self):
        self.settings = get_settings()

    def analyze_parameters(
        self, tool_name: str, parameters: dict[str, Any]
    ) -> tuple[bool, str | None]:
        """
        Analyzes tool parameters for sensitive paths, IPs, or path traversal.
        Returns (is_safe, reason).
        """
        # Convert parameters to string for scanning
        param_str = str(parameters)

        # 1. Path Traversal & Sensitive Files
        for pattern in BLOCKED_PATH_PATTERNS:
            if re.search(pattern, param_str, re.IGNORECASE):
                return False, f"Access to sensitive path or file pattern detected: {pattern}"

        # 2. Network Isolation (if tool is not explicitly allowed to use network)
        # For simplicity, we scan for blocked IP patterns
        for pattern in BLOCKED_IP_PATTERNS:
            if re.search(pattern, param_str):
                return False, f"Attempted access to restricted network endpoint: {pattern}"

        # 3. Code Injection (for shell or code interpreter tools)
        if tool_name in ("python_interpreter", "shell_command", "bash"):
            code = (
                parameters.get("code")
                or parameters.get("command")
                or parameters.get("script")
                or ""
            )
            if code:
                is_safe, reason = self.analyze_code(str(code))
                if not is_safe:
                    return False, reason

        return True, None

    def analyze_code(self, code: str) -> tuple[bool, str | None]:
        """
        Analyzes code snippets for dangerous imports or operations.
        """
        for pattern in BLOCKED_CODE_PATTERNS:
            if re.search(pattern, code):
                return False, f"Dangerous code pattern detected: {pattern}"

        return True, None

    def validate_resource_limits(
        self, parameters: dict[str, Any], limits: dict[str, Any]
    ) -> tuple[bool, str | None]:
        """
        Validates if tool requested parameters exceed safety resource limits.
        """
        # Example: if tool allows specifying timeout, cap it
        if "timeout" in parameters:
            try:
                requested_timeout = float(parameters["timeout"])
                max_timeout = limits.get("max_timeout", 60)
                if requested_timeout > max_timeout:
                    return (
                        False,
                        f"Requested timeout {requested_timeout} exceeds limit {max_timeout}",
                    )
            except (ValueError, TypeError):
                pass

        return True, None
