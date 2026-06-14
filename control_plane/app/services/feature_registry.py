from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import yaml

from app.core.config import get_settings


_SURFACE_AREA_MAP = {
    "production_core": "core",
    "production_optional": "supported",
    "beta": "beta",
    "experimental": "experimental",
    "internal": "internal",
    "deprecated": "deprecated",
}


class FeatureRegistry:
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
            config_path = os.path.join(base_dir, "config/supported-surface.yaml")
        self._config_path = config_path
        self._capabilities: Optional[List[Dict[str, Any]]] = None

    def _load(self) -> List[Dict[str, Any]]:
        if self._capabilities is not None:
            return self._capabilities
        if not os.path.exists(self._config_path):
            self._capabilities = []
            return self._capabilities
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                self._capabilities = data.get("capabilities", [])
        except Exception:
            self._capabilities = []
        return self._capabilities or []

    def get_public_capabilities(self) -> List[Dict[str, Any]]:
        settings = get_settings()
        capabilities = self._load()
        result: List[Dict[str, Any]] = []

        for cap in capabilities:
            cap_status = cap.get("status", "internal")
            if cap_status == "internal":
                continue

            feature_flag = cap.get("feature_flag")

            if feature_flag:
                flag_value = self._resolve_flag(settings, feature_flag)
                if flag_value is False:
                    continue

            capability_level = _SURFACE_AREA_MAP.get(cap_status, "experimental")
            status = self._compute_api_status(cap_status)

            item = {
                "id": cap.get("id"),
                "name": cap.get("name"),
                "status": status,
                "capability_level": capability_level,
                "limitations": cap.get("limitations", ""),
                "docs_url": cap.get("docs_url", ""),
                "since_version": cap.get("since_version", ""),
                "test_coverage": cap.get("test_coverage"),
            }
            result.append(item)

        return result

    def _compute_api_status(self, surface_status: str) -> str:
        mapping = {
            "production_core": "supported",
            "production_optional": "supported",
            "beta": "beta",
            "experimental": "experimental",
            "internal": "internal",
            "deprecated": "deprecated",
        }
        return mapping.get(surface_status, "experimental")

    def _resolve_flag(self, settings: Any, flag_name: str) -> Optional[bool]:
        if not flag_name:
            return None
        candidates = [flag_name, flag_name.upper(), flag_name.lower()]
        for candidate in candidates:
            env_val = os.environ.get(candidate)
            if env_val is not None:
                return env_val.lower() in ("true", "1", "yes")
        normalized = flag_name.lower()
        try:
            value = getattr(settings, normalized, None)
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ("true", "1", "yes")
        except Exception:
            pass
        try:
            value = getattr(settings, flag_name.upper(), None)
            if isinstance(value, bool):
                return value
        except Exception:
            pass
        return None


_registry_instance: Optional[FeatureRegistry] = None


def get_feature_registry() -> FeatureRegistry:
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = FeatureRegistry()
    return _registry_instance


def get_public_capabilities() -> List[Dict[str, Any]]:
    return get_feature_registry().get_public_capabilities()
