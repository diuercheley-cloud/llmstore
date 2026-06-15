import logging
import shlex
from typing import Any

from ..cache import LocalCache
from ..output_parsers import ParsedOutput, parse_output
from ..policy import PolicyDecision, PolicyEngine


class ShellResult:
    def __init__(
        self,
        output: str,
        returncode: int,
        blocked: bool = False,
        reason: str | None = None,
        parsed: ParsedOutput | None = None,
        cached: bool = False,
        policy_decision: PolicyDecision | None = None,
    ):
        self.output = output
        self.returncode = returncode
        self.blocked = blocked
        self.reason = reason
        self.parsed = parsed or ParsedOutput()
        self.cached = cached
        self.policy_decision = policy_decision

    def __str__(self):
        if self.blocked:
            return f"BLOCKED: {self.reason}"
        return self.output


logger = logging.getLogger(__name__)


class ShellTools:
    """
    Shell tools with unified sync and async execution logic.
    PolicyEngine is the single source of truth for security decisions.
    """

    def __init__(
        self,
        sandbox_runner,
        policy_engine: PolicyEngine | None = None,
        output_limit: int = 10000,
        cache: LocalCache | None = None,
        repo_snapshot_hash_getter=None,
        policy_hash: str = "",
        git_tools=None,
    ):
        self.sandbox = sandbox_runner
        self.policy_engine = policy_engine or PolicyEngine()
        self.output_limit = output_limit
        self.cache = cache
        self.repo_snapshot_hash_getter = repo_snapshot_hash_getter
        self.policy_hash = policy_hash
        self.git_tools = git_tools

    def _prepare_and_validate(self, command: str | list[str]) -> dict[str, Any]:
        """
        Shared command preparation and validation logic.
        """
        workspace_root = getattr(self.sandbox.workspace, "path", None)
        decision = self.policy_engine.evaluate_shell_command(command, workspace_root=workspace_root)
        return {
            "allowed": decision.allowed,
            "reason": decision.reason,
            "cmd": decision.normalized_command,
            "decision": decision,
        }

    def _process_result(
        self,
        command: str,
        returncode: int,
        stdout: str,
        stderr: str,
        allowed: bool,
        reason: str | None = None,
        cached: bool = False,
        policy_decision: PolicyDecision | None = None,
    ) -> ShellResult:
        """
        Shared result assembly and truncation logic.
        """
        if not allowed:
            return ShellResult(
                output="",
                returncode=-1,
                blocked=True,
                reason=reason,
                policy_decision=policy_decision,
            )

        output = (stdout + stderr).strip()
        if len(output) > self.output_limit:
            output = output[: self.output_limit] + "\n... [Output Truncated]"

        return ShellResult(
            output=output,
            returncode=returncode,
            parsed=parse_output(command, output, returncode),
            cached=cached,
            policy_decision=policy_decision,
        )

    def _is_read_only_command(self, command: str) -> bool:
        normalized = self.policy_engine.normalize_command(command)
        prefixes = (
            "git status",
            "git diff",
            "git rev-parse",
            "git ls-files",
            "ls",
            "find ",
            "cat ",
        )
        return normalized.startswith(prefixes)

    def _cache_key_for_command(self, command: str) -> str | None:
        if not self.cache or not self.cache.allows_read_only_tools():
            return None
        if not self._is_read_only_command(command):
            return None
        repo_snapshot_hash = (
            self.repo_snapshot_hash_getter()
            if callable(self.repo_snapshot_hash_getter)
            else "no-repo"
        )
        return self.cache.build_tool_key(
            tool="shell",
            identifier=self.policy_engine.normalize_command(command),
            repo_snapshot_hash=repo_snapshot_hash,
            policy_hash=self.policy_hash,
        )

    async def run_shell_async(self, command: str | list[str], timeout: int = 30) -> ShellResult:
        """
        Primary asynchronous implementation.
        """
        prep = self._prepare_and_validate(command)
        if not prep["allowed"]:
            return self._process_result(
                str(command),
                0,
                "",
                "",
                False,
                prep["reason"],
                policy_decision=prep["decision"],
            )

        cmd_str = prep["cmd"]
        if self.git_tools and cmd_str.startswith("git "):
            args = shlex.split(cmd_str)[1:]
            git_output = self.git_tools.run_git(args)
            returncode = 1 if git_output.startswith("Error:") else 0
            # Skip shell-level caching because git_tools already handles its own cache.
            return self._process_result(
                str(command), returncode, git_output, "", True, policy_decision=prep["decision"]
            )

        cache_key = self._cache_key_for_command(prep["cmd"])
        cache = self.cache
        if cache_key and cache:
            cached = cache.get_json("tool", cache_key)
            if cached is not None:
                return ShellResult(
                    output=str(cached.get("output", "")),
                    returncode=int(cached.get("returncode", 0)),
                    parsed=ParsedOutput(**cached.get("parsed", {})),
                    cached=True,
                    policy_decision=prep["decision"],
                )

        returncode, stdout, stderr = await self.sandbox.run_async(prep["cmd"], timeout=timeout)
        result = self._process_result(
            prep["cmd"],
            returncode,
            stdout,
            stderr,
            True,
            policy_decision=prep["decision"],
        )
        if cache_key and cache and not result.blocked:
            cache.set_json(
                "tool",
                cache_key,
                {
                    "output": result.output,
                    "returncode": result.returncode,
                    "parsed": result.parsed.to_dict(),
                },
            )
        return result

    def run_shell(self, command: str | list[str], timeout: int = 30) -> ShellResult:
        """
        Synchronous wrapper that delegates to run_shell_async.
        """
        # Delegate through sandbox.run, which already bridges async and sync execution.
        prep = self._prepare_and_validate(command)
        if not prep["allowed"]:
            return self._process_result(
                str(command),
                0,
                "",
                "",
                False,
                prep["reason"],
                policy_decision=prep["decision"],
            )

        cache_key = self._cache_key_for_command(prep["cmd"])
        cache = self.cache
        if cache_key and cache:
            cached = cache.get_json("tool", cache_key)
            if cached is not None:
                return ShellResult(
                    output=str(cached.get("output", "")),
                    returncode=int(cached.get("returncode", 0)),
                    parsed=ParsedOutput(**cached.get("parsed", {})),
                    cached=True,
                    policy_decision=prep["decision"],
                )

        returncode, stdout, stderr = self.sandbox.run(prep["cmd"], timeout=timeout)
        result = self._process_result(
            prep["cmd"],
            returncode,
            stdout,
            stderr,
            True,
            policy_decision=prep["decision"],
        )
        if cache_key and cache and not result.blocked:
            cache.set_json(
                "tool",
                cache_key,
                {
                    "output": result.output,
                    "returncode": result.returncode,
                    "parsed": result.parsed.to_dict(),
                },
            )
        return result
