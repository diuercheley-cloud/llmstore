from functools import lru_cache
from typing import Any

from control_plane.app.services.config_service import BaseAppConfig, ConfigService

# Settings remains directly constructible for isolated validation and tests.
Settings = BaseAppConfig


@lru_cache
def get_settings() -> Any:
    """
    Wrapper to provide backward compatibility with ConfigService.
    """
    return ConfigService.get_instance().config


SettingsClass = BaseAppConfig
