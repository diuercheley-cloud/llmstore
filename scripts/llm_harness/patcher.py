import logging
import os
import re
import subprocess
from hashlib import sha256

from .models import PatchResult
from .policy import PolicyEngine

logger = logging.getLogger(__name__)


class Patcher:
    """
    Applies code changes to the workspace after security validation.
    Optimized to avoid redundant git apply invocations.
    """

    def __init__(self, workspace, policy_engine: PolicyEngine):
        self.workspace = workspace
        self.policy_engine = policy_engine

    def _validate_diff_python(self, diff_content: str) -> str | None:
        """
        Runs quick Python-side validations before invoking subprocesses.
        """
        if not diff_content or not diff_content.strip():
            return "Empty diff content"

        # Verify that the payload looks like a unified diff.
        if not re.search(r"^--- ", diff_content, re.MULTILINE) or \
           not re.search(r"^\+\+\+ ", diff_content, re.MULTILINE):
            return "Invalid unified diff format"

        # Policy engine check for blocked files and dangerous patterns.
        decision = self.policy_engine.evaluate_patch(diff_content)
        if not decision.allowed:
            return f"Blocked by policy: {decision.reason}"

        return None

    def apply_patch(self, diff_content: str, dry_run: bool = False) -> PatchResult:
        """
        Executes git apply once, or --check when dry_run is enabled.
        """
        diff_sha256 = sha256(diff_content.encode("utf-8")).hexdigest()
        error_msg = self._validate_diff_python(diff_content)
        if error_msg:
            return PatchResult(
                success=False,
                error=error_msg,
                mode="check" if dry_run else "apply",
                diff_sha256=diff_sha256,
            )

        # Detect changed files for reporting.
        changed_files = re.findall(r"^\+\+\+ b/(.*)$", diff_content, re.MULTILINE)
        if not changed_files:
            # Fall back to diffs without the b/ prefix.
            changed_files = re.findall(r"^\+\+\+ (.*)$", diff_content, re.MULTILINE)

        mode = "check" if dry_run else "apply"
        cmd = ["git", "apply"]
        if dry_run:
            cmd.append("--check")

        # Use a single subprocess.run invocation.
        try:
            # Write the diff to a temporary workspace file so git can read it.
            patch_file = ".harness_patch.diff"
            self.workspace.write_file(patch_file, diff_content)
            full_patch_path = self.workspace.get_path(patch_file)

            cmd.append(full_patch_path)

            result = subprocess.run(
                cmd,
                cwd=self.workspace.path,
                capture_output=True,
                text=True
            )

            # Clean up the temporary patch file.
            if os.path.exists(full_patch_path):
                os.remove(full_patch_path)

            if result.returncode == 0:
                logger.info(f"Patch {mode} successful")
                return PatchResult(
                    success=True,
                    changed_files=changed_files,
                    mode=mode,
                    diff_sha256=diff_sha256,
                )
            else:
                stderr_clean = result.stderr.strip()
                logger.warning(f"Patch {mode} failed: {stderr_clean}")
                return PatchResult(
                    success=False,
                    error=f"git apply failed with exit code {result.returncode}",
                    stderr=stderr_clean,
                    mode=mode
                    ,
                    diff_sha256=diff_sha256,
                )

        except Exception as e:
            logger.exception("Unexpected error applying patch")
            return PatchResult(success=False, error=str(e), mode=mode, diff_sha256=diff_sha256)

    def replace_content(self, filename: str, old_str: str, new_str: str) -> bool:
        """
        Performs a simple string replacement with minimal security validation.
        Implemented via apply_patch-compatible validation for consistency.
        """
        # Build a synthetic diff so the policy engine validates the change.
        dummy_diff = f"--- {filename}\n+++ {filename}\n-{old_str}\n+{new_str}"
        decision = self.policy_engine.evaluate_patch(dummy_diff)
        if not decision.allowed:
            logger.warning(f"Content replacement blocked for {filename}: {decision.reason}")
            return False

        try:
            content = self.workspace.read_file(filename)
            if old_str not in content:
                logger.warning(f"String not found in {filename}")
                return False

            new_content = content.replace(old_str, new_str)
            self.workspace.write_file(filename, new_content)
            return True
        except Exception as e:
            logger.error(f"Failed to replace content in {filename}: {e}")
            return False

    def apply_diff(self, filename: str, diff_content: str) -> bool:
        """
        Legacy wrapper kept for compatibility.
        """
        res = self.apply_patch(diff_content)
        return res.success
