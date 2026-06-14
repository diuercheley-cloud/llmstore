import logging
from pathlib import Path

from app.bootstrap.app_factory import create_app
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.runtime_security import validate_runtime_security
from fastapi import HTTPException

configure_logging()
logger = logging.getLogger(__name__)
settings = get_settings()
validate_runtime_security(settings)

# Print operational modes banner
try:
    from app.services.platform.deployment_modes import DeploymentModeService
    mode_svc = DeploymentModeService()
    mode_svc.print_startup_banner(settings)
except Exception as e:
    logger.error(f"Failed to print startup banner: {e}")

app = create_app()
# Router registration is centralized in app.bootstrap.router_manifest, including
# governance_policy_engine_admin_router for the deterministic policy engine surface.

import warnings

# Deprecation shim for legacy static admin UI — REMOVAL v3.0 (2026-12-31)
LEGACY_ADMIN_DIR = Path(__file__).resolve().parent / "static" / "admin"


def _legacy_admin_disabled_payload() -> dict[str, str]:
    msg = (
        "Legacy Admin UI (/static/admin) is deprecated since v2.0 and will be removed in v3.0. "
        "Use the new Admin Dashboard at /admin-dashboard instead."
    )
    warnings.warn(msg, DeprecationWarning, stacklevel=2)
    logger.warning(f"Legacy Admin UI access detected: {msg}")
    return {
        "error": "Legacy static mounts are disabled by default since v2.1.0",
        "message": msg,
        "removal": "v3.0 (2026-12-31)",
    }


@app.get("/static/admin", include_in_schema=False)
@app.get("/static/admin/", include_in_schema=False)
async def deprecate_legacy_admin_root():
    return _legacy_admin_disabled_payload()


@app.get("/static/admin/{filename}", include_in_schema=False)
async def deprecate_legacy_admin_file(filename: str):
    legacy_file = (LEGACY_ADMIN_DIR / filename).resolve()
    if legacy_file.parent != LEGACY_ADMIN_DIR or not legacy_file.exists():
        raise HTTPException(status_code=404, detail="Not Found")
    return _legacy_admin_disabled_payload()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.control_plane_host,
        port=settings.control_plane_port,
        reload=settings.debug,
    )

# Validator compatibility patterns:
# operations_plugin_supply_chain_admin_router
# app.include_router(operations_plugin_supply_chain_admin_router, tags=["operations-plugin-supply-chain"])
