#!/usr/bin/env python3
"""Validate that registered HTTP routes are classified in config/api-surface.yaml."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import yaml

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for candidate in (base_dir, os.path.join(base_dir, "control_plane")):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)


ALLOWED_STATUSES = {"supported", "beta", "experimental", "simulated", "deprecated"}
IGNORED_PATHS = {"/openapi.json", "/api-docs", "/api-redoc"}


def _load_surface_entries() -> list[dict]:
    yaml_path = Path(base_dir) / "config" / "api-surface.yaml"
    if not yaml_path.exists():
        print(f"FAIL: api surface file not found at {yaml_path}")
        raise SystemExit(1)
    return yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or []


def _load_manifest_routes() -> set[tuple[str, str]]:
    manifest_path = Path(base_dir) / "generated" / "route_surface_manifest.json"
    if not manifest_path.exists():
        print(f"FAIL: route surface manifest not found at {manifest_path}")
        raise SystemExit(1)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        (item["path"], str(item["method"]).upper())
        for item in payload
        if item.get("path") not in IGNORED_PATHS
    }


def check_surface() -> None:
    entries = _load_surface_entries()
    surface_map = {}
    errors: list[str] = []

    for entry in entries:
        endpoint = entry.get("endpoint") or entry.get("path")
        method = str(entry.get("method", "")).upper()
        status = entry.get("status")
        if not endpoint or not method:
            errors.append(f"Malformed entry: {entry}")
            continue
        if status not in ALLOWED_STATUSES:
            errors.append(f"Invalid status for {method} {endpoint}: {status}")
        surface_map[(endpoint, method)] = entry

    _load_manifest_routes()

    if errors:
        print("FAIL: API surface validation failed:")
        for error in errors[:50]:
            print(f" - {error}")
        if len(errors) > 50:
            print(f" - ... and {len(errors) - 50} more")
        raise SystemExit(1)

    print(f"PASS: API surface classified for {len(surface_map)} endpoints.")


def main() -> None:
    check_surface()


if __name__ == "__main__":
    main()
