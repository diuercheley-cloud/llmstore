import json
import os
from pathlib import Path

from control_plane.app.main import app


def normalize_openapi(schema: dict) -> dict:
    if "info" in schema and "version" in schema["info"]:
        schema["info"]["version"] = "SNAPSHOT"
    if "servers" in schema:
        schema["servers"] = [{"url": "http://localhost:8080"}]

    # Remove operationId as it can be non-deterministic due to route ordering
    if "paths" in schema:
        for path in schema["paths"].values():
            for method in path.values():
                if isinstance(method, dict) and "operationId" in method:
                    del method["operationId"]

    return schema


def test_openapi_snapshot_matches():
    """
    Ensures that the current OpenAPI schema matches the saved snapshot.
    If this test fails, it means you changed the API contract.
    If the change is intentional, update the snapshot by running:
    UPDATE_SNAPSHOT=1 pytest tests/contract/test_openapi_snapshot.py
    """
    snapshot_path = Path("tests/snapshots/openapi.json")

    current_schema = app.openapi()
    normalized_schema = normalize_openapi(current_schema)

    if os.environ.get("UPDATE_SNAPSHOT") == "1":
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        with open(snapshot_path, "w", encoding="utf-8") as f:
            json.dump(normalized_schema, f, indent=2, sort_keys=True)
        print(f"Snapshot updated at {snapshot_path}")
        return

    assert snapshot_path.exists(), (
        "Snapshot file not found. Run UPDATE_SNAPSHOT=1 pytest tests/contract/test_openapi_snapshot.py"
    )

    with open(snapshot_path, encoding="utf-8") as f:
        snapshot_schema = json.load(f)

    # Compare strings for better diff in pytest
    snapshot_str = json.dumps(snapshot_schema, indent=2, sort_keys=True)
    current_str = json.dumps(normalized_schema, indent=2, sort_keys=True)

    assert current_str == snapshot_str, (
        "OpenAPI schema mismatch! If this is intentional, update the snapshot: "
        "`UPDATE_SNAPSHOT=1 pytest tests/contract/test_openapi_snapshot.py`"
    )
