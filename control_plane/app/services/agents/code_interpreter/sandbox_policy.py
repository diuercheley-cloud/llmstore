# Owner: agent-platform
import ast
import re
from dataclasses import dataclass
from typing import Any


SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{12,}"),
    re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][^'\"]+['\"]"),
]
SUSPICIOUS_PATHS = {
    ".env",
    "/etc/passwd",
    "/proc",
    "/proc/kcore",
    "/proc/keys",
    "/proc/sys",
    "/sys",
    "/dev/mem",
    "/var/run/docker.sock",
    "docker.sock",
    "data/pki",
    "uploads",
    "models",
}
FORBIDDEN_MODULES = {
    "ctypes",
    "fcntl",
    "importlib",
    "inspect",
    "os",
    "pathlib",
    "resource",
    "requests",
    "shlex",
    "shutil",
    "signal",
    "socket",
    "subprocess",
    "sys",
    "tempfile",
    "urllib",
}
FORBIDDEN_CALLS = {
    "compile",
    "eval",
    "exec",
    "globals",
    "locals",
    "open",
    "breakpoint",
    "__import__",
}


class SandboxPolicyViolation(Exception):
    def __init__(self, reason: str, details: dict[str, Any] | None = None):
        super().__init__(reason)
        self.reason = reason
        self.details = details or {}


@dataclass
class PolicyDecision:
    decision: str
    reason: str
    metadata: dict[str, Any]


class SandboxPolicyEngine:
    def validate_code(self, code: str) -> list[PolicyDecision]:
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            raise SandboxPolicyViolation("Code contains invalid syntax", {"line": exc.lineno}) from exc

        decisions: list[PolicyDecision] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    if root in FORBIDDEN_MODULES:
                        raise SandboxPolicyViolation(
                            f"Import of '{root}' is not allowed",
                            {"module": root, "lineno": getattr(node, 'lineno', None)},
                        )
            if isinstance(node, ast.ImportFrom):
                root = (node.module or "").split(".")[0]
                if root in FORBIDDEN_MODULES:
                    raise SandboxPolicyViolation(
                        f"Import of '{root}' is not allowed",
                        {"module": root, "lineno": getattr(node, 'lineno', None)},
                    )
            if isinstance(node, ast.Call):
                func_name = self._call_name(node.func)
                if func_name in FORBIDDEN_CALLS:
                    raise SandboxPolicyViolation(
                        f"Call to '{func_name}' is not allowed",
                        {"call": func_name, "lineno": getattr(node, 'lineno', None)},
                    )
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                decision = self._inspect_string(node.value)
                if decision:
                    decisions.append(decision)
        return decisions

    def validate_artifact_content(self, content: bytes) -> None:
        decoded = content.decode("utf-8", errors="ignore")
        for pattern in SECRET_PATTERNS:
            if pattern.search(decoded):
                raise SandboxPolicyViolation("Artifact contains secret-like content", {"pattern": pattern.pattern})

    def truncate_output(self, output: str, max_bytes: int) -> tuple[str, bool]:
        encoded = output.encode("utf-8")
        if len(encoded) <= max_bytes:
            return output, False
        truncated = encoded[:max_bytes].decode("utf-8", errors="ignore")
        return truncated + "\n...[truncated]", True

    def _inspect_string(self, value: str) -> PolicyDecision | None:
        normalized = value.strip()
        for path in SUSPICIOUS_PATHS:
            if path in normalized:
                raise SandboxPolicyViolation(
                    "Access to protected path is not allowed",
                    {"path": path},
                )
        if normalized.startswith("http://") or normalized.startswith("https://"):
            raise SandboxPolicyViolation("Network access is disabled by default", {"target": normalized})
        if "169.254.169.254" in normalized or "metadata.google.internal" in normalized or "169.254.170.2" in normalized:
            raise SandboxPolicyViolation("Metadata endpoint access is disabled by default", {"target": normalized})
        return None

    def _call_name(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        return None
