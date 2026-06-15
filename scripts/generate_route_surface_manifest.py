import json
import os
import sys
from pathlib import Path

import yaml

# Add control_plane to sys.path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(root_dir / "control_plane"))

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET", "static-secret-for-surface-generation-only")
os.environ.setdefault("ADMIN_TOKEN", "static-token-for-surface-generation-only")
os.environ.setdefault("AGENT_RUNTIME_ENABLED", "true")
os.environ.setdefault("AGENT_EXECUTION_ENABLED", "true")
os.environ.setdefault("COMMERCIAL_GLOBAL_ROUTING_ENABLED", "true")

from app.bootstrap.app_factory import create_app
from fastapi.routing import APIRoute


def load_yaml(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or []


def generate_manifest():
    app = create_app()
    api_surface = load_yaml(root_dir / "config/api-surface.yaml")
    supported_surface = load_yaml(root_dir / "config/supported-surface.yaml")

    # Pre-process surfaces for faster lookup
    api_surface_map = {
        (item["endpoint"], item["method"]): item
        for item in api_surface
        if "endpoint" in item and "method" in item
    }

    capabilities = (
        supported_surface.get("capabilities", []) if isinstance(supported_surface, dict) else []
    )

    manifest = []

    def fallback_surface(path: str, module: str):
        internal_prefixes = (
            "/admin",
            "/api/admin",
            "/api/v1/admin",
            "/api/v1/agent-service",
            "/api/v1/alerts",
            "/api/agents",
            "/api/audit",
            "/api/backends",
            "/api/multimodal",
            "/auth",
            "/billing",
            "/mcp",
            "/hub",
            "/harness",
            "/tests",
            "/examples",
            "/admin-dashboard",
            "/admin-v2",
            "/client-portal",
        )
        internal_module_markers = (
            ".admin",
            "_admin",
            "app.api.system",
            "app.api.auth",
            "app.api.billing_payments",
            "app.api.alert_webhooks",
            "app.api.multimodal_v2",
            "app.api.audit",
            "app.api.agent_service",
            "app.api.agent_deployments",
            "app.api.agent_mcp_admin",
        )
        if path.startswith(internal_prefixes) or any(
            marker in module for marker in internal_module_markers
        ):
            return {
                "status": "internal",
                "owner": "platform-ops",
                "doc_link": "/docs/api/supported-api-surface.md",
                "feature_flag": None,
            }
        return None

    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue

        path = route.path
        methods = list(route.methods)

        for method in methods:
            route_id = (
                f"{method}_{path.replace('/', '_').replace('{', '').replace('}', '').strip('_')}"
            )
            module = route.endpoint.__module__

            # Heuristic for domain/profile based on module
            domain = "unknown"
            if "admin" in module:
                domain = "admin"
            elif "commercial" in module:
                domain = "commercial"
            elif "operations" in module:
                domain = "operations"
            elif "portal" in module:
                domain = "portal"
            elif "client" in module or "mobile" in module:
                domain = "client"
            elif "rag" in module:
                domain = "rag"
            elif "auth" in module:
                domain = "auth"
            elif "system" in module or "public" in module:
                domain = "core"

            # Lookup in api-surface.yaml
            surface_item = api_surface_map.get((path, method))

            # Lookup in supported-surface.yaml for feature flag and status
            matched_capability = None
            for cap in capabilities:
                prefix = cap.get("api_prefix")
                if prefix and path.startswith(prefix):
                    matched_capability = cap
                    break

            status = "unclassified"
            owner = "unknown"
            doc_link = None
            feature_flag = None

            if surface_item:
                status = surface_item.get("status", status)
                owner = surface_item.get("owner", owner)
                doc_link = surface_item.get("docs_url", doc_link)

            if matched_capability:
                if status == "unclassified":
                    status = matched_capability.get("status", status)
                if owner == "unknown":
                    owner = matched_capability.get("owner", owner)
                if not doc_link:
                    doc_link = matched_capability.get("docs_url", doc_link)
                feature_flag = matched_capability.get("feature_flag")

            if status == "unclassified":
                fallback = fallback_surface(path, module)
                if fallback:
                    status = fallback["status"]
                    owner = fallback["owner"]
                    doc_link = fallback["doc_link"]
                    feature_flag = fallback["feature_flag"]

            # Normalize route statuses for generated docs and governance checks.
            status_map = {
                "production_core": "core",
                "production_optional": "supported",
                "beta": "beta",
                "experimental": "experimental",
                "simulated": "simulated",
                "deprecated": "deprecated",
                "internal": "internal",
            }
            status = status_map.get(status, status)
            if status == "supported" and "core" in path:  # additional heuristic
                status = "core"

            manifest.append(
                {
                    "route_id": route_id,
                    "path": path,
                    "method": method,
                    "router_module": module,
                    "domain": domain,
                    "profile": domain,  # using domain as profile for now
                    "feature_flag_required": feature_flag,
                    "status": status,
                    "owner": owner,
                    "doc_link": doc_link,
                }
            )

    # Save to generated/route_surface_manifest.json
    generated_dir = root_dir / "generated"
    generated_dir.mkdir(exist_ok=True)

    output_path = generated_dir / "route_surface_manifest.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Generated manifest with {len(manifest)} routes at {output_path}")


if __name__ == "__main__":
    generate_manifest()
