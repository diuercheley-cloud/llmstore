import logging
import os
import re
import shlex
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ShellCommandAnalysis(BaseModel):
    normalized_command: str
    main_command: str | None = None
    args: list[str] = Field(default_factory=list)
    chain_operators: list[str] = Field(default_factory=list)
    redirections: list[str] = Field(default_factory=list)
    command_substitutions: list[str] = Field(default_factory=list)
    tokens: list[str] = Field(default_factory=list)
    target_paths: list[str] = Field(default_factory=list)
    parse_error: str | None = None


class PolicyDecision(BaseModel):
    allowed: bool
    reason: str | None = None
    normalized_command: str | None = None
    policy_level: str | None = None
    policy_rule: str | None = None
    analysis: dict[str, Any] = Field(default_factory=dict)


class PolicyEngine:
    """
    Single source of truth for security and governance in the LLM Harness.
    Centralizes shell, file path, and patch validation.
    """

    HARD_DENY_PATTERNS = [
        (r"\bsudo\b", "sudo"),
        (r"curl\s+.*\s*\|\s*sh", "curl|sh"),
        (r"wget\s+.*\s*\|\s*sh", "wget|sh"),
        (r"docker\s+system\s+prune", "docker-system-prune"),
        (r"git\s+push", "git-push"),
        (r"\.env", "dot-env"),
        (r"id_rsa", "id-rsa"),
        (r"secrets", "secrets"),
    ]

    SENSITIVE_PATH_PATTERNS = [r"\.env", r"key", r"secret", r"\.git"]

    def __init__(self, config: dict[str, Any] | None = None):
        base_config = {
            "max_tokens": 10000,
            "max_cost": 1.0,
            "max_llm_calls_per_minute": 10,
            "allowed_tools": ["ls", "cat", "grep", "git", "pytest", "python3", "echo"],
            "shell_policy": {
                "workspace_root": ".",
                "global_deny": {
                    "commands": [],
                    "patterns": [],
                    "paths": ["/"],
                },
                "workspace_allow": {
                    "enabled": True,
                },
                "command_allow": {},
                "path_exceptions": [],
            },
        }
        self.config = self._deep_merge(base_config, config or {})
        self.allowed_base_commands = self.config.get("allowed_tools", [])
        shell_policy = self.config.get("shell_policy", {})
        shell_policy.setdefault("workspace_root", ".")
        shell_policy.setdefault("global_deny", {})
        shell_policy.setdefault("workspace_allow", {"enabled": True})
        shell_policy.setdefault("command_allow", {})
        shell_policy.setdefault("path_exceptions", [])
        self.shell_policy = shell_policy
        self.allow_mcp_tools = self.config.get("allow_mcp_tools", False)
        self._llm_call_history: list[float] = []

    def _deep_merge(self, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        merged = dict(base)
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = self._deep_merge(merged[key], value)
            else:
                merged[key] = value
        return merged

    def check_usage(self, tokens: int, cost: float) -> bool:
        if tokens > self.config["max_tokens"]:
            logger.warning(f"Token limit exceeded: {tokens} > {self.config['max_tokens']}")
            return False
        if cost > self.config["max_cost"]:
            logger.warning(f"Cost limit exceeded: {cost} > {self.config['max_cost']}")
            return False

        # Rate limit check for LLM calls per minute
        now = time.time()
        minute_ago = now - 60
        self._llm_call_history = [t for t in self._llm_call_history if t > minute_ago]

        limit = self.config.get("max_llm_calls_per_minute", 10)
        if len(self._llm_call_history) >= limit:
            logger.warning(
                f"Rate limit exceeded: {len(self._llm_call_history)} calls "
                f"in last minute (limit={limit})"
            )
            return False

        return True

    def record_llm_call(self):
        """Records a successful LLM call for rate limiting."""
        self._llm_call_history.append(time.time())

    def normalize_command(self, command: str | list[str]) -> str:
        cmd_str = " ".join(command) if isinstance(command, list) else command
        cmd_str = cmd_str.replace("\n", " ").strip()
        cmd_str = re.sub(r"\s+", " ", cmd_str)
        return cmd_str

    def _scan_shell_features(self, command: str) -> tuple[list[str], list[str], list[str]]:
        chain_ops: list[str] = []
        redirections: list[str] = []
        substitutions: list[str] = []
        in_single = False
        in_double = False
        i = 0
        while i < len(command):
            ch = command[i]
            if ch == "'" and not in_double:
                in_single = not in_single
                i += 1
                continue
            if ch == '"' and not in_single:
                in_double = not in_double
                i += 1
                continue
            if in_single or in_double:
                i += 1
                continue

            two = command[i : i + 2]
            three = command[i : i + 3]
            if ch == "`":
                substitutions.append("`")
            elif two == "$(":
                substitutions.append("$(")
            elif two in ("&&", "||"):
                chain_ops.append(two)
                i += 2
                continue
            elif ch in (";", "|"):
                chain_ops.append(ch)
            elif three == "<<<":
                redirections.append("<<<")
                i += 3
                continue
            elif two in ("<<", ">>"):
                redirections.append(two)
                i += 2
                continue
            elif ch in ("<", ">"):
                redirections.append(ch)
            i += 1
        return chain_ops, redirections, substitutions

    def analyze_shell_command(self, command: str | list[str]) -> ShellCommandAnalysis:
        normalized = self.normalize_command(command)
        chain_ops, redirections, substitutions = self._scan_shell_features(normalized)
        try:
            tokens = shlex.split(normalized, posix=True)
        except ValueError as exc:
            return ShellCommandAnalysis(
                normalized_command=normalized,
                chain_operators=chain_ops,
                redirections=redirections,
                command_substitutions=substitutions,
                parse_error=str(exc),
            )

        main_command = tokens[0] if tokens else None
        args = tokens[1:] if len(tokens) > 1 else []
        target_paths = [arg for arg in args if not arg.startswith("-")]
        return ShellCommandAnalysis(
            normalized_command=normalized,
            main_command=main_command,
            args=args,
            chain_operators=chain_ops,
            redirections=redirections,
            command_substitutions=substitutions,
            tokens=tokens,
            target_paths=target_paths,
        )

    def _build_decision(
        self,
        allowed: bool,
        reason: str | None,
        analysis: ShellCommandAnalysis | None = None,
        policy_level: str | None = None,
        policy_rule: str | None = None,
    ) -> PolicyDecision:
        payload = analysis.model_dump() if analysis else {}
        return PolicyDecision(
            allowed=allowed,
            reason=reason,
            normalized_command=analysis.normalized_command if analysis else None,
            policy_level=policy_level,
            policy_rule=policy_rule,
            analysis=payload,
        )

    def _workspace_root(self, workspace_root: str | None = None) -> Path:
        configured = workspace_root or self.shell_policy.get("workspace_root") or "."
        return Path(configured).resolve()

    def _resolve_path(self, raw_path: str, workspace_root: str | None = None) -> Path:
        root = self._workspace_root(workspace_root)
        candidate = Path(raw_path)
        if candidate.is_absolute():
            return candidate.resolve()
        return (root / candidate).resolve()

    def _is_within_workspace(self, raw_path: str, workspace_root: str | None = None) -> bool:
        root = self._workspace_root(workspace_root)
        resolved = self._resolve_path(raw_path, workspace_root)
        try:
            resolved.relative_to(root)
            return True
        except ValueError:
            return False

    def _matches_path_exception(
        self,
        analysis: ShellCommandAnalysis,
        workspace_root: str | None = None,
    ) -> dict[str, Any] | None:
        exceptions = self.shell_policy.get("path_exceptions", [])
        for exception in exceptions:
            if exception.get("command") != analysis.main_command:
                continue
            required_args = exception.get("args", [])
            if any(req not in analysis.args for req in required_args):
                continue
            target = exception.get("path")
            if not target:
                continue
            if target not in analysis.target_paths:
                continue
            if not self._is_within_workspace(target, workspace_root):
                continue
            resolved_target = self._resolve_path(target, workspace_root)
            if resolved_target == Path("/"):
                continue
            return exception
        return None

    def evaluate_shell_command(
        self,
        command: str | list[str],
        workspace_root: str | None = None,
    ) -> PolicyDecision:
        from .tracing import Tracer
        with Tracer().trace_span(
            "policy_check", attributes={"policy_level": "shell", "command": str(command)}
        ):
            from .plugins import plugin_registry
            for name, rule_fn in plugin_registry.list_policy_rules().items():
                try:
                    res = rule_fn(command)
                    if isinstance(res, bool) and not res:
                        return PolicyDecision(
                            allowed=False, reason=f"Blocked by plugin policy rule: {name}"
                        )
                    elif isinstance(res, PolicyDecision) and not res.allowed:
                        return res
                except Exception as e:
                    logger.error(f"Plugin policy rule {name} failed: {e}")
            return self._evaluate_shell_command_inner(command, workspace_root)

    def _evaluate_shell_command_inner(
        self,
        command: str | list[str],
        workspace_root: str | None = None,
    ) -> PolicyDecision:
        analysis = self.analyze_shell_command(command)

        if analysis.parse_error:
            return self._build_decision(
                False,
                f"Shell parsing failed: {analysis.parse_error}",
                analysis,
                policy_level="semantic",
                policy_rule="parse-error",
            )

        if analysis.chain_operators:
            operator = analysis.chain_operators[0]
            return self._build_decision(
                False,
                f"Dangerous shell operator detected: {operator}",
                analysis,
                policy_level="semantic",
                policy_rule="chain-operator",
            )

        if analysis.command_substitutions:
            operator = analysis.command_substitutions[0]
            return self._build_decision(
                False,
                f"Command substitution detected: {operator}",
                analysis,
                policy_level="semantic",
                policy_rule="command-substitution",
            )

        if analysis.redirections:
            operator = analysis.redirections[0]
            return self._build_decision(
                False,
                f"Shell redirection detected: {operator}",
                analysis,
                policy_level="semantic",
                policy_rule="redirection",
            )

        normalized = analysis.normalized_command
        global_deny = self.shell_policy.get("global_deny", {})
        hard_patterns = list(self.HARD_DENY_PATTERNS)
        hard_patterns.extend(
            [(pattern, pattern) for pattern in global_deny.get("patterns", [])]
        )
        for pattern, label in hard_patterns:
            if re.search(pattern, normalized, re.IGNORECASE):
                return self._build_decision(
                    False,
                    f"Forbidden command or pattern detected: {label}",
                    analysis,
                    policy_level="global_deny",
                    policy_rule=label,
                )

        hard_deny_commands = set(global_deny.get("commands", []))
        if analysis.main_command in hard_deny_commands:
            return self._build_decision(
                False,
                f"Command '{analysis.main_command}' denied by global policy",
                analysis,
                policy_level="global_deny",
                policy_rule="command",
            )

        for target in analysis.target_paths:
            resolved = self._resolve_path(target, workspace_root)
            if str(resolved) in set(global_deny.get("paths", [])) or resolved == Path("/"):
                return self._build_decision(
                    False,
                    "Destructive root path access is always denied",
                    analysis,
                    policy_level="global_deny",
                    policy_rule="root-path",
                )

        if analysis.main_command == "rm" and any(arg in ("-rf", "-fr") for arg in analysis.args):
            for target in analysis.target_paths:
                resolved = self._resolve_path(target, workspace_root)
                if resolved == Path("/"):
                    return self._build_decision(
                        False,
                        "Destructive root path access is always denied",
                        analysis,
                        policy_level="global_deny",
                        policy_rule="rm-root",
                    )

        workspace_policy = self.shell_policy.get("workspace_allow", {})
        if workspace_policy.get("enabled", True):
            for target in analysis.target_paths:
                if not self._is_within_workspace(target, workspace_root):
                    return self._build_decision(
                        False,
                        f"Path '{target}' escapes the workspace",
                        analysis,
                        policy_level="workspace_allow",
                        policy_rule="workspace-boundary",
                    )

        command_allow = self.shell_policy.get("command_allow", {})
        main_cmd = analysis.main_command
        main_cmd_lower = main_cmd.lower() if main_cmd else None

        explicit_allow = command_allow.get(main_cmd)
        if explicit_allow is None and main_cmd_lower:
            explicit_allow = command_allow.get(main_cmd_lower)

        allowed_tools_lower = [c.lower() for c in self.allowed_base_commands]
        default_allowed = (
            main_cmd in self.allowed_base_commands or
            (main_cmd_lower in allowed_tools_lower if main_cmd_lower else False)
        )
        command_is_allowed = explicit_allow if explicit_allow is not None else default_allowed

        if command_is_allowed:
            return self._build_decision(
                True,
                None,
                analysis,
                policy_level="command_allow",
                policy_rule="base-command",
            )

        exception = self._matches_path_exception(analysis, workspace_root)
        if exception:
            return self._build_decision(
                True,
                None,
                analysis,
                policy_level="path_exception",
                policy_rule=exception.get("name", exception.get("path", "path-exception")),
            )

        return self._build_decision(
            False,
            f"Command '{analysis.main_command}' is not in the allowlist",
            analysis,
            policy_level="command_allow",
            policy_rule="missing-command-allow",
        )

    def evaluate_file_path(self, path: str) -> PolicyDecision:
        from .tracing import Tracer
        with Tracer().trace_span(
            "policy_check", attributes={"policy_level": "file_path", "path": path}
        ):
            from .plugins import plugin_registry
            for name, rule_fn in plugin_registry.list_policy_rules().items():
                try:
                    res = rule_fn(path)
                    if isinstance(res, bool) and not res:
                        return PolicyDecision(
                            allowed=False, reason=f"Blocked by plugin policy rule: {name}"
                        )
                    elif isinstance(res, PolicyDecision) and not res.allowed:
                        return res
                except Exception as e:
                    logger.error(f"Plugin policy rule {name} failed: {e}")
            normalized_path = os.path.normpath(path)

            if normalized_path.startswith("..") or normalized_path.startswith("/"):
                return PolicyDecision(
                    allowed=False, reason="Path traversal or absolute path detected"
                )

            for pattern in self.SENSITIVE_PATH_PATTERNS:
                if re.search(pattern, normalized_path, re.IGNORECASE):
                    reason = f"Access to sensitive file pattern forbidden: {pattern}"
                    return PolicyDecision(allowed=False, reason=reason)

            return PolicyDecision(allowed=True)

    def evaluate_patch(self, diff: str) -> PolicyDecision:
        from .tracing import Tracer
        with Tracer().trace_span("policy_check", attributes={"policy_level": "patch"}):
            from .plugins import plugin_registry
            for name, rule_fn in plugin_registry.list_policy_rules().items():
                try:
                    res = rule_fn(diff)
                    if isinstance(res, bool) and not res:
                        return PolicyDecision(
                            allowed=False, reason=f"Blocked by plugin policy rule: {name}"
                        )
                    elif isinstance(res, PolicyDecision) and not res.allowed:
                        return res
                except Exception as e:
                    logger.error(f"Plugin policy rule {name} failed: {e}")
            forbidden_files = ["policy.py", "sandbox.py", ".env", "Makefile"]
            for f in forbidden_files:
                if f"--- {f}" in diff or f"+++ {f}" in diff:
                    return PolicyDecision(allowed=False, reason=f"Patching {f} is forbidden")

            for pattern, label in self.HARD_DENY_PATTERNS:
                if re.search(r"^\+.*" + pattern, diff, re.MULTILINE | re.IGNORECASE):
                    reason = f"Patch adds forbidden command: {label}"
                    return PolicyDecision(allowed=False, reason=reason)

            return PolicyDecision(allowed=True)

    def describe_for_agent(self) -> str:
        description = "## Security & Execution Policy\n"
        description += f"Allowed tools (shell): {', '.join(self.allowed_base_commands)}\n"
        description += "Global deny: sudo, root deletion, curl|sh, git push, secrets.\n"
        description += (
            "Shell parser blocks chain operators, command substitution "
            "and redirection.\n"
        )
        description += (
            "Workspace boundary: commands must stay inside the workspace "
            "unless denied.\n"
        )
        description += "Execution Environment: Isolated Sandbox (No Internet).\n"
        description += "Strategy: Prefer 'apply_patch' or 'replace_content' for code changes. "
        description += "Run tests often to verify changes.\n"
        return description
