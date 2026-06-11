#!/usr/bin/env python3
import json
import uuid
from datetime import datetime, timezone
import os

def main():
    lock_path = "uv.lock"
    sbom_path = "sbom.json"
    
    if not os.path.exists(lock_path):
        print(f"Error: {lock_path} not found. Run `uv lock` first.")
        return 1

    try:
        import tomllib
    except ImportError:
        import pip._vendor.tomli as tomllib  # Fallback

    with open(lock_path, "rb") as f:
        lock_data = tomllib.load(f)

    packages = lock_data.get("package", [])
    
    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{uuid.uuid4()}",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "component": {
                "name": "llm-harness",
                "version": "1.0.0",
                "type": "application"
            }
        },
        "components": []
    }

    for pkg in packages:
        name = pkg.get("name")
        version = pkg.get("version")
        if name and version:
            sbom["components"].append({
                "name": name,
                "version": version,
                "type": "library",
                "purl": f"pkg:pypi/{name}@{version}"
            })

    # Sort components by name for deterministic generation
    sbom["components"].sort(key=lambda c: c["name"])

    with open(sbom_path, "w", encoding="utf-8") as f:
        json.dump(sbom, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"SBOM successfully generated with {len(sbom['components'])} components in {sbom_path}")
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
