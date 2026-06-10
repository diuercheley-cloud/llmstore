import os
import sys

import yaml

# Add control_plane to python path
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, os.path.join(base_dir, "control_plane"))

from app.main import app
from starlette.routing import Route


def generate():
    yaml_path = os.path.join(base_dir, "config/api-surface.yaml")
    
    # Load existing to preserve manual overrides if run repeatedly
    existing_recs = {}
    if os.path.exists(yaml_path):
        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or []
                for entry in data:
                    key = (entry["endpoint"], entry["method"])
                    existing_recs[key] = entry
        except Exception:
            pass

    records = []
    seen = set()

    for route in app.routes:
        if not isinstance(route, Route):
            continue
        path = route.path
        methods = route.methods or ["GET"]
        for method in methods:
            if (path, method) in seen:
                continue
            seen.add((path, method))

            # If already exists, preserve it
            if (path, method) in existing_recs:
                records.append(existing_recs[(path, method)])
                continue

            # Determine default metadata
            owner = "platform-ops"
            status = "supported"
            replacement = None
            since_version = "1.0.0"
            deprecation_version = None
            docs_url = "/docs/api/supported-api-surface.md"

            # 1. Model management duplicates
            if path.startswith("/admin/models/runtime"):
                status = "deprecated"
                replacement = "/admin/models/lifecycle"
                since_version = "1.8.0"
                deprecation_version = "1.9.7"
                owner = "model-ops"
                docs_url = None

            # 2. Legacy admin endpoints replaced by Admin v2
            # E.g. legacy billing under /admin/billing/
            elif path.startswith("/admin/billing") and "commercial" not in path:
                status = "deprecated"
                replacement = "/admin/commercial/billing"
                since_version = "1.5.0"
                deprecation_version = "1.9.7"
                owner = "billing-ops"
                docs_url = None
            elif path.startswith("/admin/legacy"):
                status = "deprecated"
                since_version = "1.4.0"
                deprecation_version = "1.9.7"
                docs_url = None

            # 3. Experimental endpoints
            elif "experimental" in path or "experimental" in getattr(route, "tags", []):
                # Mark as deprecated if no docs, or experimental if we add docs_url
                status = "experimental"
                owner = "research-ops"
                docs_url = None  # Will be flagged as missing docs and needs deprecation or docs_url

            # Determine owner by path prefixes
            if "billing" in path:
                owner = "billing-ops"
            elif "security" in path or "abuse" in path or "attestation" in path:
                owner = "security-ops"
            elif "commercial" in path:
                owner = "commercial-ops"

            records.append({
                "endpoint": path,
                "method": method,
                "owner": owner,
                "status": status,
                "replacement": replacement,
                "since_version": since_version,
                "deprecation_version": deprecation_version,
                "docs_url": docs_url
            })

    # Sort records for clean yaml structure
    records.sort(key=lambda r: (r["endpoint"], r["method"]))

    os.makedirs(os.path.dirname(yaml_path), exist_ok=True)
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(records, f, sort_keys=False, allow_unicode=True)

    print(f"Generated {len(records)} entries in config/api-surface.yaml")

if __name__ == "__main__":
    generate()
