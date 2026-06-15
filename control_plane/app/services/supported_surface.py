import os
from typing import Any

import yaml


class SupportedSurfaceService:
    def __init__(self, config_path: str | None = None):
        if config_path is None:
            # Locate relative to the root directory
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
            config_path = os.path.join(base_dir, "config/supported-surface.yaml")
        self.config_path = config_path
        self._capabilities: list[dict[str, Any]] | None = None

    def _load_capabilities(self) -> list[dict[str, Any]]:
        if self._capabilities is not None:
            return self._capabilities

        if not os.path.exists(self.config_path):
            self._capabilities = []
            return self._capabilities

        try:
            with open(self.config_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                self._capabilities = data.get("capabilities", [])
        except Exception:
            self._capabilities = []

        return self._capabilities or []

    def get_all_capabilities(self) -> list[dict[str, Any]]:
        return self._load_capabilities()

    def get_capability_by_id(self, cap_id: str) -> dict[str, Any] | None:
        caps = self._load_capabilities()
        for cap in caps:
            if cap.get("id") == cap_id:
                return cap
        return None

    def get_capabilities_by_status(self, status: str) -> list[dict[str, Any]]:
        caps = self._load_capabilities()
        return [cap for cap in caps if cap.get("status") == status]
