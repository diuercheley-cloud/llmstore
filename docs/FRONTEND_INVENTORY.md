# Frontend Inventory & Consolidation Plan

| Path | Purpose | Status | Owner | Route/Deploy | Orphaned? | Action |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `frontend/admin` | Main Admin Dashboard | Official | admin-team | `/admin` | No | Keep |
| `frontend/client` | Client Portal | Official | client-team | `/` | No | Keep |
| `control_plane/app/static/admin` | Legacy Admin UI | Legacy | core-team | `/static/admin` (Disabled) | Yes | Deprecate/Remove |
| `control_plane/app/static/admin-lab` | Legacy Lab UI | Legacy | core-team | `/static/admin-lab` (Disabled) | Yes | Deprecate/Remove |
| `control_plane/app/static/admin-v2` | Legacy Admin V2 | Legacy | core-team | `/static/admin-v2` (Disabled) | Yes | Deprecate/Remove |
| `control_plane/app/static/portal` | Legacy Portal | Legacy | core-team | `/static/portal` (Disabled) | Yes | Deprecate/Remove |
| `control_plane/app/static/harness` | Dev Harness | Experimental| core-team | `/static/harness` (Disabled) | No | Keep/Refactor |
| `control_plane/app/static/monitoring` | Monitoring UI | Legacy | core-team | `/static/monitoring` (Disabled) | Yes | Replace with Tempo/Grafana |

## Consolidation Strategy
1. **Official UIs**: Only `frontend/admin` and `frontend/client` are official and will be built/deployed separately.
2. **Static/Legacy**: All `control_plane/app/static/*` legacy UIs are **disabled by default** since v2.1.0 (set `ENABLE_LEGACY_STATIC=true` to re-enable temporarily).
3. **Decoupling**: Remove static builds from the FastAPI repository and backend deployment. Configure NGINX/Caddy to serve the builds from a dedicated location.
