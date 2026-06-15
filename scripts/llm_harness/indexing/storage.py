import json
import os
from typing import Any


class IndexStorage:
    def __init__(self, workspace_root: str = "."):
        self.workspace_root = workspace_root
        self.index_dir = os.path.join(workspace_root, ".llm_harness_index")

    def ensure_dir(self) -> None:
        os.makedirs(self.index_dir, exist_ok=True)

    def save_json(self, filename: str, data: Any) -> None:
        self.ensure_dir()
        path = os.path.join(self.index_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load_json(self, filename: str) -> Any:
        path = os.path.join(self.index_dir, filename)
        if not os.path.exists(path):
            return None
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
