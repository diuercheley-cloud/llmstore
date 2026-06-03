import logging
import os
import shutil
import tempfile

from .defaults import TEMP_BASE_DIR

logger = logging.getLogger(__name__)


class Workspace:
    """
    Manages a temporary directory for agent execution.
    """

    def __init__(self, base_path: str | None = None, temp_base_dir: str | None = TEMP_BASE_DIR):
        self.base_path = base_path
        self.temp_base_dir = temp_base_dir
        self.path: str | None = None

    async def __aenter__(self):
        if self.base_path:
            self.path = os.path.abspath(self.base_path)
            os.makedirs(self.path, exist_ok=True)
        else:
            self.path = tempfile.mkdtemp(prefix="agent-harness-", dir=self.temp_base_dir)

        logger.info(f"Workspace initialized at {self.path}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if not self.base_path and self.path and os.path.exists(self.path):
            logger.info(f"Cleaning up workspace at {self.path}")
            shutil.rmtree(self.path)

    def get_path(self, *subpaths: str) -> str:
        if self.path is None:
            raise RuntimeError("Workspace not initialized. Use 'async with' context manager.")
        root = os.path.abspath(self.path)
        target = os.path.abspath(os.path.join(root, *subpaths))
        if target != root and not target.startswith(root + os.sep):
            raise PermissionError("Path escapes the workspace root")
        return target

    def write_file(self, filename: str, content: str):
        full_path = self.get_path(filename)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            f.write(content)
        return full_path

    def read_file(self, filename: str) -> str:
        with open(self.get_path(filename)) as f:
            return f.read()
