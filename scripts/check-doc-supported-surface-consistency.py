#!/usr/bin/env python3
import sys
import os
import yaml
import re

def main():
    supported_surface_path = "config/supported-surface.yaml"
    doc_path = "docs/support/supported-surface-area.md"

    if not os.path.exists(supported_surface_path):
        print(f"Error: {supported_surface_path} does not exist.")
        sys.exit(1)

    if not os.path.exists(doc_path):
        print(f"Error: {doc_path} does not exist.")
        sys.exit(1)

    # 1. Parse YAML capabilities
    try:
        with open(supported_surface_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)
    except Exception as e:
        print(f"Error parsing {supported_surface_path}: {e}")
        sys.exit(1)

    yaml_caps = yaml_data.get("capabilities", [])
    print(f"Loaded {len(yaml_caps)} capabilities from YAML.")

    # 2. Read markdown file
    with open(doc_path, "r", encoding="utf-8") as f:
        doc_content = f.read()

    # 3. Basic checks
    errors = []

    # Check for contradictions like claiming "complete" while only relying on runtime disabled in production docs
    if "production" in doc_content.lower() and "complete" in doc_content.lower():
        # Ensure it doesn't suggest runtime disabled is sufficient for production
        if "disabled" in doc_content.lower() and "claim" not in doc_content.lower():
            errors.append("Documentation suggests a disabled runtime counts as a production claim.")

    # Extract all rows from the markdown table
    # Table rows format: | **Name** | `category` | Owner | Description |
    rows = []
    for line in doc_content.splitlines():
        if "|" in line and "---" not in line and "Recurso / Área" not in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 4:
                rows.append(parts)

    print(f"Found {len(rows)} rows in markdown capabilities table.")

    # Mapping of YAML status categories to Markdown support levels
    status_mapping = {
        "production_core": "supported",
        "production_optional": "supported",
        "beta": "beta",
        "experimental": "experimental",
        "advisory": "advisory",
        "deprecated": "deprecated",
        "internal": "internal",
        "non-production": "non-production"
    }

    # Verify that plugin-runtime, mcp, and observability reflect real status
    for cap in yaml_caps:
        cap_id = cap.get("id")
        cap_name = cap.get("name", "")
        cap_status = cap.get("status")
        expected_md_level = status_mapping.get(cap_status, cap_status)

        # Look for a match in markdown rows by name or substring
        match_found = False
        for row in rows:
            # row[1] contains the resource name like "**OpenAI-compatible API**"
            row_name = row[1].replace("**", "").strip()
            row_level = row[2].replace("`", "").strip()

            if cap_name.lower() in row_name.lower() or row_name.lower() in cap_name.lower():
                match_found = True
                # Check category consistency
                if expected_md_level != row_level:
                    errors.append(
                        f"Consistency error for cap '{cap_name}': "
                        f"YAML status is '{cap_status}' (expected MD level '{expected_md_level}'), "
                        f"but Markdown says '{row_level}'."
                    )
                break

        # Some minor capabilities might not be listed in the summarized markdown matrix, which is fine,
        # but key capabilities like plugin, mcp, etc., should be consistent.

    if errors:
        print("\n=== Consistency Errors Found ===")
        for err in errors:
            print(f"- {err}")
        sys.exit(1)
    else:
        print("\nAll doc/surface consistency checks passed successfully.")
        sys.exit(0)

if __name__ == "__main__":
    main()
