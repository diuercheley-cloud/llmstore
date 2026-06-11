import os
import sys
import json
import yaml
from pathlib import Path

# Add control_plane to sys.path
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir / "control_plane"))

from fastapi.routing import APIRoute
from app.bootstrap.app_factory import create_app

def load_yaml(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or []

def generate_manifest():
    app = create_app()
    api_surface = load_yaml(root_dir / "config/api-surface.yaml")
    supported_surface = load_yaml(root_dir / "config/supported-surface.yaml")
    
    # Pre-process surfaces for faster lookup
    api_surface_map = {(item["endpoint"], item["method"]): item for item in api_surface if "endpoint" in item and "method" in item}
    
    capabilities = supported_surface.get("capabilities", []) if isinstance(supported_surface, dict) else []
    
    manifest = []
    
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
            
        path = route.path
        methods = list(route.methods)
        
        for method in methods:
            route_id = f"{method}_{path.replace('/', '_').replace('{', '').replace('}', '').strip('_')}"
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

            # Map statuses to requested set
            # requested: core, supported, beta, experimental, legacy, deprecated, internal
            status_map = {
                "production_core": "core",
                "production_optional": "supported",
                "keep_supported": "supported",
                "beta": "beta",
                "keep_beta": "beta",
                "experimental": "experimental",
                "deprecated": "deprecated",
                "internal": "internal"
            }
            status = status_map.get(status, status)
            if status == "supported" and "core" in path: # additional heuristic
                 status = "core"

            manifest.append({
                "route_id": route_id,
                "path": path,
                "method": method,
                "router_module": module,
                "domain": domain,
                "profile": domain, # using domain as profile for now
                "feature_flag_required": feature_flag,
                "status": status,
                "owner": owner,
                "doc_link": doc_link
            })
            
    # Save to generated/route_surface_manifest.json
    generated_dir = root_dir / "generated"
    generated_dir.mkdir(exist_ok=True)
    
    output_path = generated_dir / "route_surface_manifest.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    
    print(f"Generated manifest with {len(manifest)} routes at {output_path}")

if __name__ == "__main__":
    generate_manifest()
