import os
from pathlib import Path

import yaml


class FlagLoader:
    def __init__(self, profile: str = "production"):
        self.profile = profile
        self.config_path = Path(__file__).resolve().parents[3] / "config/flags.yml"
        self.flags = self._load_config()

    def _load_config(self):
        with open(self.config_path) as f:
            return yaml.safe_load(f)

    def get(self, key: str, default=None):
        # Search hierarchy: env override -> profile -> product/rollout
        # 1. Env Overrides (e.g. FF_ABUSE_DETECTION_ENABLED)
        env_key = f"FF_{key}"
        if env_key in os.environ:
            return os.environ[env_key].lower() == "true"

        # 2. Hierarchy search
        for category in ["environment", "product", "rollout", "experiment", "legacy"]:
            data = self.flags.get(category, {})
            if category == "environment":
                if self.profile in data and key in data[self.profile]:
                    return data[self.profile][key]
            elif key in data:
                return data[key]
        return default
