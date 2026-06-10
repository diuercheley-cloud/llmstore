# API Router Governance

## Context
To ensure predictability and maintainability of our API surface, all routes must be registered via a central `router_manifest.py`. This policy prohibits auto-discovery of routers.

## Registration Process
1. All new routers must be added to `control_plane/app/bootstrap/router_manifest.py`.
2. Each entry must specify:
   - `module`: The import path for the router.
   - `router_name`: The variable name of the router within that module.
   - `prefix`: The URL prefix.
   - `tags`: List of tags for OpenAPI documentation.
   - `status`: One of `supported`, `beta`, `legacy`.
3. Routes marked as `legacy` require a migration plan for removal.

## Enforcement
The `bootstrap/routers.py` loader strictly consumes the manifest. Any router not declared in the manifest will not be exposed by the application.
