import importlib
import logging
import pkgutil

from app.core.config import get_settings
from fastapi import APIRouter, FastAPI

logger = logging.getLogger(__name__)


def register_routers(app: FastAPI, package_name: str = "app.api") -> None:
    """
    Dynamically discover and register all FastAPI routers in a package.
    Respects 'REQUIRED_FLAG' (string) or 'is_enabled(settings)' (callable)
    module-level attributes for feature flagging.
    """
    try:
        package = importlib.import_module(package_name)
    except ImportError as e:
        logger.error(f"Failed to import router package {package_name}: {e}")
        return

    settings = get_settings()
    seen_routers: set[int] = set()

    for _, module_name, _ in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
        try:
            module = importlib.import_module(module_name)

            # Check for feature flag
            if hasattr(module, "REQUIRED_FLAG"):
                flag_name = module.REQUIRED_FLAG
                if not getattr(settings, flag_name, False):
                    continue

            if hasattr(module, "is_enabled"):
                is_enabled_fn = module.is_enabled
                if not is_enabled_fn(settings):
                    continue

            # Also check for module level router configuration like PREFIX or TAGS
            prefix = getattr(module, "ROUTER_PREFIX", "")
            tags = getattr(module, "ROUTER_TAGS", None)

            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, APIRouter):
                    identity = id(attr)
                    if identity not in seen_routers:
                        seen_routers.add(identity)
                        kwargs = {}
                        if prefix and not attr.prefix:
                            kwargs["prefix"] = prefix
                        if tags and not attr.tags:
                            kwargs["tags"] = tags

                        app.include_router(attr, **kwargs)
        except Exception as e:
            logger.warning(
                f"Skipping router auto-discovery for module {module_name} due to error: {e}"
            )
