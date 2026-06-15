import gzip
import json
import logging
import os
import shutil
import time
from datetime import datetime
from typing import Any

from .sanitizer import Sanitizer

logger = logging.getLogger(__name__)


class LocalMemory:
    def __init__(
        self,
        memory_dir: str = ".llm_harness_memory",
        retention_days: int = 30,
        max_file_size_mb: int = 10,
        compress_rotated: bool = True,
    ):
        self.memory_dir = memory_dir
        self.retention_days = retention_days
        self.max_file_size_mb = max_file_size_mb
        self.compress_rotated = compress_rotated
        os.makedirs(self.memory_dir, exist_ok=True)
        self.memory_file = os.path.join(self.memory_dir, "runs.jsonl")

    def record_run(self, task: str, result: dict[str, Any]):
        # Double check secrets redaction
        sanitized_task = Sanitizer.sanitize_text(task)
        sanitized_result = Sanitizer.sanitize_data(result)

        entry = {
            "timestamp": time.time(),
            "date": datetime.now().isoformat(),
            "task": sanitized_task,
            "success": sanitized_result.get("success", False),
            "message": sanitized_result.get("message"),
            "error": sanitized_result.get("error"),
            "changed_files": sanitized_result.get("metrics", {}).get("changed_files", []),
            "total_tokens": sanitized_result.get("total_tokens", 0),
            "estimated_cost": sanitized_result.get("estimated_cost", 0.0),
        }

        self._rotate_if_needed()

        try:
            with open(self.memory_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to record run to memory: {e}")

        self._cleanup_old_entries()

    def _rotate_if_needed(self):
        if not os.path.exists(self.memory_file):
            return

        try:
            if os.path.getsize(self.memory_file) > self.max_file_size_mb * 1024 * 1024:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                rotated_file = os.path.join(self.memory_dir, f"runs_{timestamp}.jsonl")
                os.rename(self.memory_file, rotated_file)
                logger.info(f"Rotated memory file: {rotated_file}")

                if self.compress_rotated:
                    self._compress_file(rotated_file)
        except Exception as e:
            logger.error(f"Memory rotation failed: {e}")

    def _compress_file(self, file_path: str):
        try:
            with open(file_path, "rb") as f_in:
                with gzip.open(f"{file_path}.gz", "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
            os.remove(file_path)
            logger.info(f"Compressed rotated memory: {file_path}.gz")
        except Exception as e:
            logger.error(f"Failed to compress memory file: {e}")

    def get_recent_history(self, limit: int = 5) -> list[dict[str, Any]]:
        if not os.path.exists(self.memory_file):
            return []

        entries = []
        try:
            with open(self.memory_file) as f:
                for line in f:
                    if line.strip():
                        entries.append(json.loads(line))
        except Exception as e:
            logger.error(f"Failed to read memory: {e}")

        # Return most recent first
        return sorted(entries, key=lambda x: x["timestamp"], reverse=True)[:limit]

    def store_eval_feedback(self, suite_name: str, feedback: str):
        path = os.path.join(self.memory_dir, "eval_feedback.jsonl")
        entry = {
            "timestamp": time.time(),
            "date": datetime.now().isoformat(),
            "suite_name": suite_name,
            "feedback": feedback,
        }
        try:
            with open(path, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to store eval feedback: {e}")

    def get_latest_eval_feedback(self) -> str | None:
        path = os.path.join(self.memory_dir, "eval_feedback.jsonl")
        if not os.path.exists(path):
            return None

        last_feedback = None
        try:
            with open(path) as f:
                for line in f:
                    if line.strip():
                        last_feedback = json.loads(line).get("feedback")
        except Exception as e:
            logger.error(f"Failed to read eval feedback: {e}")

        return last_feedback

    def _cleanup_old_entries(self):
        cutoff = time.time() - (self.retention_days * 24 * 3600)

        # 1. Cleanup old rotated files
        for f in os.listdir(self.memory_dir):
            if f == "runs.jsonl":
                continue

            f_path = os.path.join(self.memory_dir, f)
            try:
                if os.path.getmtime(f_path) < cutoff:
                    os.remove(f_path)
                    logger.info(f"Removed old memory file: {f}")
            except OSError:
                continue

        # 2. Cleanup entries within current runs.jsonl
        if not os.path.exists(self.memory_file):
            return

        remaining = []
        needed_cleanup = False

        try:
            with open(self.memory_file) as handle_in:
                for line in handle_in:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        if entry.get("timestamp", 0) > cutoff:
                            remaining.append(line)
                        else:
                            needed_cleanup = True
                    except json.JSONDecodeError:
                        needed_cleanup = True

            if needed_cleanup:
                with open(self.memory_file, "w") as handle_out:
                    handle_out.writelines(remaining)
                logger.debug("Cleaned up old memory entries from active file")
        except Exception as e:
            logger.error(f"Failed to cleanup memory: {e}")

    def get_context_for_prompt(self, limit: int = 3) -> str:
        history = self.get_recent_history(limit=limit)
        if not history:
            return ""

        lines = ["Recent task history:"]
        for entry in history:
            status = "Success" if entry.get("success") else "Failed"
            date = entry.get("date", "").split("T")[0]
            lines.append(f"- {date} [{status}]: {entry.get('task')}")
            if not entry.get("success") and entry.get("error"):
                lines.append(f"  Error: {entry.get('error')}")
            elif entry.get("changed_files"):
                files = ", ".join(entry.get("changed_files", [])[:3])
                lines.append(f"  Modified: {files}")

        return "\n".join(lines)
