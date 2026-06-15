#!/usr/bin/env python3
import os
import re
import sys

import yaml

SUPPORTED_SURFACE_YAML = "config/supported-surface.yaml"
CANONICAL_DOCS = [
    "README.md",
    "docs/index.md",
    "docs/CANONICAL_INDEX.md",
    "docs/platform/supported-surface.md",
    "docs/support/supported-surface-area.md",
    "docs/api/supported-api-surface.md",
]


def load_capabilities():
    with open(SUPPORTED_SURFACE_YAML) as f:
        data = yaml.safe_load(f)
        return data.get("capabilities", [])


def check_contradictions(content, file_path):
    errors = []

    contradictory_pairs = [
        (r"no real plugin execution", r"sandboxed local execution"),
        (r"attestation is policy-only", r"hardware-backed trust"),
    ]

    for p1, p2 in contradictory_pairs:
        if re.search(p1, content, re.I) and re.search(p2, content, re.I):
            errors.append(f"Contradiction found in {file_path}: '{p1}' vs '{p2}'")

    return errors


def check_canonical_surface_rules(content, file_path):
    errors = []
    banned_patterns = [
        r"^\*\*Core:\*\*",
        r"^\*\*Beta:\*\*",
        r"^\*\*Experimental:\*\*",
        r"^\*\*Legacy:\*\*",
        r"^\*\*Simulated Flows:\*\*",
    ]

    if file_path != "docs/PRODUCT_SURFACE.md":
        for pattern in banned_patterns:
            if re.search(pattern, content, re.MULTILINE):
                errors.append(
                    f"{file_path} contains manual capability tier lists; use docs/PRODUCT_SURFACE.md instead"
                )

    if file_path in CANONICAL_DOCS and "PRODUCT_SURFACE.md" not in content:
        errors.append(f"{file_path} must reference docs/PRODUCT_SURFACE.md")

    if "file://" in content:
        errors.append(f"{file_path} contains absolute file:// links")

    return errors


def main():
    if not os.path.exists(SUPPORTED_SURFACE_YAML):
        print(f"Error: {SUPPORTED_SURFACE_YAML} not found")
        return

    capabilities = load_capabilities()
    cap_map = {c["id"]: c for f in capabilities for c in [f] if "id" in f}

    print("--- Running Documentation Consistency Check ---")

    files_to_check = [
        "docs/architecture/platform_overview.md",
        "docs/architecture/platform_guarantees_and_limitations.md",
        "README.md",
        "SECURITY.md",
        "docs/index.md",
        "docs/CANONICAL_INDEX.md",
        "docs/platform/supported-surface.md",
        "docs/support/supported-surface-area.md",
        "docs/api/supported-api-surface.md",
    ]

    overall_errors = 0

    for file_path in files_to_check:
        if not os.path.exists(file_path):
            print(f"[SKIP] {file_path} not found")
            continue

        print(f"Checking {file_path}...")
        with open(file_path) as f:
            content = f.read()

        file_errors = check_contradictions(content, file_path)
        file_errors.extend(check_canonical_surface_rules(content, file_path))
        for err in file_errors:
            print(f" - [FAIL] {err}")
            overall_errors += 1

        for cap_id, cap_info in cap_map.items():
            name = cap_info["name"]
            status = cap_info["status"]

            if status in ["supported", "production_ready"]:
                if re.search(f"- no real {name.lower()}", content, re.I):
                    print(
                        f" - [FAIL] {file_path} claims 'no real {name}' but capability is '{status}'"
                    )
                    overall_errors += 1

    if overall_errors > 0:
        print(f"\nTotal Errors: {overall_errors}")
        sys.exit(1)
    else:
        print("\nOK: Documentation is consistent.")
        sys.exit(0)


if __name__ == "__main__":
    main()
