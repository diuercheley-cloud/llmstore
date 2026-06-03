import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

class CheckpointManager:
    def __init__(self, checkpoint_dir: str = ".llm_harness_checkpoints"):
        self.checkpoint_dir = checkpoint_dir
        os.makedirs(self.checkpoint_dir, exist_ok=True)

    def save_checkpoint(self, run_id: str, state: dict[str, Any]):
        path = os.path.join(self.checkpoint_dir, f"{run_id}.json")
        try:
            with open(path, "w") as f:
                json.dump(state, f, indent=2)
            logger.info(f"Checkpoint saved for run {run_id}")
        except Exception as e:
            logger.error(f"Failed to save checkpoint {run_id}: {e}")

    def load_checkpoint(self, run_id: str) -> dict[str, Any] | None:
        path = os.path.join(self.checkpoint_dir, f"{run_id}.json")
        if not os.path.exists(path):
            logger.warning(f"Checkpoint not found for run {run_id}")
            return None

        try:
            with open(path) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load checkpoint {run_id}: {e}")
            return None

    def list_checkpoints(self) -> list[str]:
        return [f[:-5] for f in os.listdir(self.checkpoint_dir) if f.endswith(".json")]
