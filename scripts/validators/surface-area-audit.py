#!/usr/bin/env python3
# Owner: platform-ops
import os
import sys

import yaml

# Add control_plane to python path
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(base_dir, "control_plane"))

from app.services.platform.surface_audit import SurfaceAuditService


def validate_ga_surface():
    api_surface_path = os.path.join(base_dir, "config/api-surface.yaml")
    if os.path.exists(api_surface_path):
        with open(api_surface_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or []

        errors = []
        for entry in data:
            path = entry.get("path") or entry.get("endpoint", "unknown")
            method = entry.get("method", "unknown")
            ref = f"{method} {path}"

            if not entry.get("owner"):
                errors.append(f"{ref} sem owner")
            if not entry.get("status"):
                errors.append(f"{ref} sem status")
            if "auth_required" not in entry:
                errors.append(f"{ref} sem auth classification")

            status = entry.get("status", "")
            if status in ["supported", "beta", "experimental"] and not entry.get("docs_url"):
                if "internal" not in status:  # internal ones might not need public docs
                    errors.append(f"{ref} public sem docs")

            if status in ["beta", "experimental"] and (
                not entry.get("feature_flag") or entry.get("feature_flag") == "none"
            ):
                errors.append(f"{ref} beta/experimental sem feature flag")

            if status == "deprecated":
                if not entry.get("replacement") and not entry.get("justification"):
                    errors.append(f"{ref} deprecated sem replacement ou justification")

        if os.environ.get("GA_MODE") == "true" and errors:
            print("GA Validation Failed for API Surface:")
            for err in errors:
                print(f" - {err}")
            sys.exit(1)


def generate_markdown_reports():
    validate_ga_surface()
    print("Running platform surface area audit...")
    service = SurfaceAuditService(base_dir=base_dir)
    audit_results = service.run_audit()

    # 1. Create artifacts directory if not exists
    artifacts_dir = os.path.join(base_dir, "artifacts/platform")
    os.makedirs(artifacts_dir, exist_ok=True)

    # 2. Write surface-audit.md
    audit_md_path = os.path.join(artifacts_dir, "surface-audit.md")

    apis = audit_results["apis"]
    ui = audit_results["ui_pages"]
    srv = audit_results["services"]
    scr = audit_results["scripts"]
    ff = audit_results["feature_flags"]
    adp = audit_results["adapters"]
    db = audit_results["dashboards"]
    tst = audit_results["tests"]

    # Classify components for the report
    with open(audit_md_path, "w", encoding="utf-8") as f:
        f.write("# Platform Surface Area Audit\n\n")
        f.write(
            "Generated platform surface area audit report tracking operational complexity and dead code.\n\n"
        )

        f.write("## 1. APIs Audit\n")
        f.write(f"- **Duplicate Routes ({len(apis['duplicates'])})**:\n")
        if apis["duplicates"]:
            for d in apis["duplicates"]:
                f.write(f"  - `{d}`\n")
        else:
            f.write("  - None\n")

        f.write(f"- **Unreferenced Registry ({len(apis['unreferenced_registry'])})**:\n")
        if apis["unreferenced_registry"]:
            for u in apis["unreferenced_registry"]:
                f.write(f"  - `{u}`\n")
        else:
            f.write("  - None\n")

        unclassified_len = len(apis.get("unclassified", []))
        if unclassified_len > 0:
            f.write(f"- **Unclassified Endpoints ({unclassified_len})**:\n")
            for u in apis["unclassified"]:
                f.write(f"  - `{u}`\n")

        f.write(f"- **Unregistered Routes ({len(apis['unregistered_routes'])})**:\n")
        if apis["unregistered_routes"]:
            for u in apis["unregistered_routes"]:
                f.write(f"  - `{u}`\n")
        else:
            f.write("  - None\n")

        f.write("\n## 2. Pages UI Audit\n")
        f.write(f"- **Orphaned UI Pages ({len(ui['orphaned_pages'])})**:\n")
        if ui["orphaned_pages"]:
            for p in ui["orphaned_pages"]:
                f.write(f"  - `{p}`\n")
        else:
            f.write("  - None\n")

        f.write("\n## 3. Services Audit\n")
        f.write(f"- **Orphaned Services ({len(srv['orphaned_services'])})**:\n")
        if srv["orphaned_services"]:
            for s in srv["orphaned_services"]:
                f.write(f"  - `{s}`\n")
        else:
            f.write("  - None\n")

        f.write("\n## 4. Scripts Audit\n")
        f.write(f"- **Orphaned Scripts ({len(scr['orphaned_scripts'])})**:\n")
        if scr["orphaned_scripts"]:
            for s in scr["orphaned_scripts"]:
                f.write(f"  - `{s}`\n")
        else:
            f.write("  - None\n")

        f.write("\n## 5. Feature Flags Audit\n")
        f.write(f"- **Orphaned Feature Flags ({len(ff['orphaned_flags'])})**:\n")
        if ff["orphaned_flags"]:
            for flg in ff["orphaned_flags"]:
                f.write(f"  - `{flg}`\n")
        else:
            f.write("  - None\n")

        f.write("\n## 6. Tool Adapters Audit\n")
        f.write(f"- **Unregistered Tool Adapters ({len(adp['unregistered_adapters'])})**:\n")
        if adp["unregistered_adapters"]:
            for a in adp["unregistered_adapters"]:
                f.write(f"  - `{a}`\n")
        else:
            f.write("  - None\n")

        f.write("\n## 7. Dashboards Audit\n")
        f.write(f"- **Unprovisioned Dashboards ({len(db['unprovisioned_dashboards'])})**:\n")
        if db["unprovisioned_dashboards"]:
            for d in db["unprovisioned_dashboards"]:
                f.write(f"  - `{d}`\n")
        else:
            f.write("  - None\n")

        f.write("\n## 8. Test Coverage Audit\n")
        f.write(f"- **Useless Test Files ({len(tst['useless_test_files'])})**:\n")
        if tst["useless_test_files"]:
            for t in tst["useless_test_files"]:
                f.write(f"  - `{t}`\n")
        else:
            f.write("  - None\n")

    print(f"Audit report written to {audit_md_path}")

    # 3. Write deprecation-report.md
    dep_md_path = os.path.join(artifacts_dir, "deprecation-report.md")
    with open(dep_md_path, "w", encoding="utf-8") as f:
        f.write("# API Deprecation & Sunset Report\n\n")
        f.write(
            "List of deprecated endpoints in the platform's API surface with active sunset schedules.\n\n"
        )
        f.write(
            "| Endpoint | Method | Sunset Date | Replacement / Migration Path | Required Headers |\n"
        )
        f.write("| :--- | :--- | :--- | :--- | :--- |\n")

        deprecated_list = apis["deprecated_apis"]
        if deprecated_list:
            for dep in deprecated_list:
                endpoint = dep["endpoint"]
                method = dep["method"]
                replacement = dep["replacement"] or "None"
                sunset_date = dep["sunset_date"]
                headers = "`X-Deprecated-Endpoint`, `Sunset`, `X-Sunset-Date`"
                f.write(
                    f"| `{endpoint}` | `{method}` | {sunset_date} | `{replacement}` | {headers} |\n"
                )
        else:
            f.write("| - | - | - | - | - |\n")

    print(f"Deprecation report written to {dep_md_path}")

    # Also write a copy to control_plane/artifacts/ if required by release gate
    cp_artifacts_dir = os.path.join(base_dir, "control_plane/artifacts/platform")
    os.makedirs(cp_artifacts_dir, exist_ok=True)
    with open(os.path.join(cp_artifacts_dir, "surface-audit.md"), "w", encoding="utf-8") as f:
        with open(audit_md_path, encoding="utf-8") as src:
            f.write(src.read())
    with open(os.path.join(cp_artifacts_dir, "deprecation-report.md"), "w", encoding="utf-8") as f:
        with open(dep_md_path, encoding="utf-8") as src:
            f.write(src.read())


if __name__ == "__main__":
    generate_markdown_reports()
