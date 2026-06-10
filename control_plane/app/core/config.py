from functools import lru_cache
from typing import Any, Optional, Tuple, List, Self
from .config_agent import AgentSettings
from .config_commercial import CommercialSettings
from .cors import get_cors_warnings, resolve_cors_origins
from control_plane.app.services.config_service import ConfigService

# Maintain backward compatibility for Settings
class Settings:
    """
    Wrapper to provide backward compatibility with ConfigService.
    Can be used as a type hint (Settings | None) or as a factory Settings().
    """
    def __new__(cls, *args, **kwargs) -> Any:
        return ConfigService.get_instance().config

@lru_cache
def get_settings() -> Any:
    """
    Wrapper to provide backward compatibility with ConfigService.
    """
    return ConfigService.get_instance().config

# For type hinting compatibility, we might need to expose the actual class
SettingsClass = type(ConfigService.get_instance().config)
