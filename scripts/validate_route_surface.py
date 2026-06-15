import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

root_dir = Path(__file__).parent.parent


def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_yaml(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or []


def check_tests(path):
    # Search for the path in the tests directory
    # We escape the path for grep
    try:
        # Simple heuristic: grep for the path string in tests/
        # We use -r for recursive, -l for list files, -q for quiet
        result = subprocess.run(
            ["grep", "-rl", path, str(root_dir / "tests")], capture_output=True, text=True
        )
        return len(result.stdout.strip()) > 0
    except Exception:
        return False


def validate():
    manifest_path = root_dir / "generated/route_surface_manifest.json"
    if not manifest_path.exists():
        print("Manifest not found. Run generate_route_surface_manifest.py first.")
        sys.exit(1)

    manifest = load_json(manifest_path)
    api_surface = load_yaml(root_dir / "config/api-surface.yaml")

    errors = []
    warnings = []

    # 1. Rota nova não estiver classificada
    for route in manifest:
        if route["status"] == "unclassified":
            errors.append(
                f"Unclassified route: {route['method']} {route['path']} (Module: {route['router_module']})"
            )

        # 3. Rota supported/core não tiver teste mínimo
        if route["status"] in ["core", "supported"]:
            if not route["doc_link"]:
                errors.append(
                    f"Missing doc_link for {route['status']} route: {route['method']} {route['path']}"
                )

            # This check can be slow, maybe we only do it for a subset or optimize it
            # For now, let's include it as requested
            if not check_tests(route["path"]):
                warnings.append(
                    f"No minimal test found for {route['status']} route: {route['method']} {route['path']}"
                )

        # 4. Rota legacy/deprecated não tiver prazo ou shim documentado
        if route["status"] in ["legacy", "deprecated"]:
            # Check if it has a doc_link or if it has a replacement in api-surface.yaml
            has_replacement = False
            for item in api_surface:
                if item.get("endpoint") == route["path"] and item.get("method") == route["method"]:
                    if item.get("replacement"):
                        has_replacement = True
                        break

            if not route["doc_link"] and not has_replacement:
                errors.append(
                    f"Missing documentation or replacement for {route['status']} route: {route['method']} {route['path']}"
                )

    # 2. Rota documentada não existir mais
    # Check api-surface.yaml against current routes
    manifest_routes = {(r["path"], r["method"]) for r in manifest}
    for item in api_surface:
        endpoint = item.get("endpoint")
        method = item.get("method")
        if endpoint and method and (endpoint, method) not in manifest_routes:
            # Some endpoints might be regex or have placeholders, manifest should have the same format from FastAPI
            # FastAPI uses {param} format, same as api-surface.yaml usually
            warnings.append(f"Documented route no longer exists: {method} {endpoint}")

    if errors:
        print(f"Validation failed with {len(errors)} errors:")
        for err in errors[:20]:  # Limit output
            print(f"  - {err}")
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more errors.")
        sys.exit(1)
    else:
        if warnings:
            print(f"Validation successful with {len(warnings)} warnings:")
            for warning in warnings[:20]:
                print(f"  - {warning}")
            if len(warnings) > 20:
                print(f"  ... and {len(warnings) - 20} more warnings.")
            sys.exit(0)
        print("Validation successful!")
        sys.exit(0)


if __name__ == "__main__":
    validate()
