import contextlib
import hashlib
import json
import logging
import subprocess
import time
from pathlib import Path
from typing import Any, Literal, cast

from .sanitizer import Sanitizer

logger = logging.getLogger(__name__)

CacheMode = Literal["disabled", "llm", "read-only"]


class LocalCache:
    def __init__(
        self,
        mode: CacheMode = "disabled",
        cache_dir: str = ".llm_harness_cache",
        ttl_seconds: int | None = None,
        max_entries: int = 1000,
    ):
        self.mode = mode
        self.cache_dir = Path(cache_dir)
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        if self.mode != "disabled":
            self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Stats
        self.hits = 0
        self.misses = 0
        self.expired = 0
        self.evicted = 0

    @property
    def enabled(self) -> bool:
        return self.mode != "disabled"

    def allows_llm(self) -> bool:
        return self.mode in {"llm", "read-only"}

    def allows_read_only_tools(self) -> bool:
        return self.mode == "read-only"

    def get_json(self, namespace: str, key: str) -> Any | None:
        if not self.enabled and namespace != "capabilities":
            return None

        path = self._entry_path(namespace, key)
        if not path.exists():
            if self.enabled:
                self.misses += 1
            return None

        try:
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)

            created_at = payload.get("created_at", 0)
            if self.ttl_seconds and (time.time() - created_at > self.ttl_seconds):
                if self.enabled:
                    self.expired += 1
                logger.debug(f"Cache entry expired: {namespace}/{key}")
                # Optionally delete expired file
                with contextlib.suppress(OSError):
                    path.unlink()
                return None

            if self.enabled:
                self.hits += 1
            return payload.get("value")
        except Exception as e:
            logger.error(f"Failed to read cache entry {namespace}/{key}: {e}")
            if self.enabled:
                self.misses += 1
            return None

    def set_json(self, namespace: str, key: str, value: Any) -> None:
        if not self.enabled and namespace != "capabilities":
            return

        # Periodic cleanup if we are over max entries (simplified)
        # In a real system, we'd use a more efficient LRU
        if self.enabled and self.max_entries > 0:
            self.cleanup_expired()

        path = self._entry_path(namespace, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "created_at": int(time.time()),
            "value": Sanitizer.sanitize_data(value),
        }
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)

    def cleanup_expired(self) -> None:
        """Removes expired entries and enforces max_entries limit."""
        if not self.enabled:
            return

        all_entries = []
        now = time.time()

        for p in self.cache_dir.rglob("*.json"):
            if not p.is_file():
                continue
            try:
                # We could just check mtime for efficiency, but let's be thorough
                # if ttl is small.
                mtime = p.stat().st_mtime
                if self.ttl_seconds and (now - mtime > self.ttl_seconds):
                    p.unlink()
                    self.expired += 1
                    continue
                all_entries.append(p)
            except OSError:
                continue

        # Enforce max_entries (LRU approximate via mtime)
        if len(all_entries) > self.max_entries:
            all_entries.sort(key=lambda x: x.stat().st_mtime)
            to_delete = len(all_entries) - self.max_entries
            for i in range(to_delete):
                try:
                    all_entries[i].unlink()
                    self.evicted += 1
                except OSError:
                    continue

    def get_stats(self) -> dict[str, int]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "expired": self.expired,
            "evicted": self.evicted,
        }

    def build_llm_key(
        self,
        *,
        provider: str,
        model: str,
        messages: list[dict[str, Any]],
        task: str,
        repo_snapshot_hash: str,
        policy_hash: str,
    ) -> str:
        return self._hash_payload(
            {
                "provider": provider,
                "model": model,
                "prompt_hash": self._hash_payload(Sanitizer.sanitize_data(messages)),
                "task_hash": self._hash_payload(Sanitizer.sanitize_text(task)),
                "repo_snapshot_hash": repo_snapshot_hash,
                "policy_hash": policy_hash,
            }
        )

    def build_tool_key(
        self,
        *,
        tool: str,
        identifier: str,
        repo_snapshot_hash: str,
        policy_hash: str,
    ) -> str:
        return self._hash_payload(
            {
                "tool": tool,
                "identifier": Sanitizer.sanitize_text(identifier),
                "repo_snapshot_hash": repo_snapshot_hash,
                "policy_hash": policy_hash,
            }
        )

    def compute_policy_hash(self, policy_description: str) -> str:
        return self._hash_payload(Sanitizer.sanitize_text(policy_description))

    def compute_repo_snapshot_hash(self, workspace_path: str | None) -> str:
        if not workspace_path:
            return "no-workspace"
        git_hash = self._git_snapshot_hash(workspace_path)
        if git_hash:
            return git_hash
        return self._filesystem_snapshot_hash(workspace_path)

    def _entry_path(self, namespace: str, key: str) -> Path:
        return self.cache_dir / namespace / f"{key}.json"

    def _hash_payload(self, payload: Any) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def _git_snapshot_hash(self, workspace_path: str) -> str | None:
        try:
            head = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=workspace_path,
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            ).stdout.strip()
            status = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=workspace_path,
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            ).stdout
            return self._hash_payload({"head": head, "status": status})
        except Exception:
            return None

    def _filesystem_snapshot_hash(self, workspace_path: str) -> str:
        digest = hashlib.sha256()
        root = Path(workspace_path)
        if not root.exists():
            return "missing-workspace"
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            rel = path.relative_to(root)
            ignored = {".git", "__pycache__", ".mypy_cache", ".pytest_cache"}
            if any(part in ignored for part in rel.parts):
                continue
            digest.update(str(rel).encode("utf-8"))
            try:
                digest.update(path.read_bytes())
            except OSError:
                digest.update(b"[unreadable]")
        return digest.hexdigest()


def resolve_cache_mode(cache: str | None, no_cache: bool = False) -> CacheMode:
    if no_cache:
        return "disabled"
    if cache in {None, ""}:
        return "disabled"
    if cache not in {"disabled", "llm", "read-only"}:
        raise ValueError(f"Invalid cache mode: {cache}")
    return cast(CacheMode, cache)
