import os
import sys

import yaml

# Add control_plane to python path
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(base_dir, "control_plane"))

from app.main import app
from starlette.routing import Route


def check_surface():
    yaml_path = os.path.join(base_dir, "config/api-surface.yaml")
    
    if not os.path.exists(yaml_path):
        print(f"FAIL: config/api-surface.yaml not found at {yaml_path}")
        sys.exit(1)
        
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or []
    except Exception as e:
        print(f"FAIL: Error reading config/api-surface.yaml: {e}")
        sys.exit(1)

    # Build mapping
    registry = {}
    for entry in data:
        key = (entry.get("endpoint"), entry.get("method"))
        registry[key] = entry

    failures = []
    checked_count = 0

    for route in app.routes:
        if not isinstance(route, Route):
            continue
        path = route.path
        methods = route.methods or ["GET"]
        for method in methods:
            checked_count += 1
            key = (path, method)
            
            if key not in registry:
                failures.append(f"Endpoint '{method} {path}' is unclassified (missing from config/api-surface.yaml).")
            else:
                entry = registry[key]
                status = entry.get("status")
                docs_url = entry.get("docs_url")
                
                if status == "experimental" and not docs_url:
                    failures.append(f"Experimental endpoint '{method} {path}' is missing documentation (docs_url is null or empty).")

    if failures:
        print("--- API Surface Audit Failed ---")
        for f in failures:
            print(f" - {f}")
        print(f"Total failures: {len(failures)} / Checked: {checked_count}")
        sys.exit(1)
    else:
        print(f"PASS: All {checked_count} endpoints successfully classified and verified.")
        sys.exit(0)

if __name__ == "__main__":
    check_surface()
