import json
import os
import sys
from pathlib import Path

# Add project root to PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET", "static-secret-for-openapi-snapshot")
os.environ.setdefault("ADMIN_TOKEN", "static-token-for-openapi-snapshot")

from control_plane.app.main import app


def normalize_openapi(schema: dict) -> dict:
    # Remove version as it changes with every release
    if "info" in schema and "version" in schema["info"]:
        schema["info"]["version"] = "SNAPSHOT"

    # Remove servers as they might depend on local env
    if "servers" in schema:
        schema["servers"] = [{"url": "http://localhost:8080"}]

    # Remove operationId as it can be non-deterministic due to route ordering
    if "paths" in schema:
        for path in schema["paths"].values():
            for method in path.values():
                if isinstance(method, dict) and "operationId" in method:
                    del method["operationId"]

    return schema


def main():
    schema = app.openapi()
    normalized = normalize_openapi(schema)

    snapshot_path = Path("tests/snapshots/openapi.json")
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)

    with open(snapshot_path, "w", encoding="utf-8") as f:
        json.dump(normalized, f, indent=2, sort_keys=True)

    print(f"OpenAPI snapshot generated at {snapshot_path}")


if __name__ == "__main__":
    main()
