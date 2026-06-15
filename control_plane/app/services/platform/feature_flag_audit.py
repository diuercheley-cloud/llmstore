import os
from datetime import UTC, datetime
from typing import Any

import yaml
from app.services.feature_flag_registry import FeatureFlagRegistryService


class FeatureFlagAuditService:
    def __init__(self, registry_path: str | None = None):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
        if registry_path is None:
            registry_path = os.path.join(base_dir, "config/feature-flags.yaml")
        self.registry_path = registry_path
        self.registry_service = FeatureFlagRegistryService(registry_path=registry_path)

    def load_raw_flags(self) -> list[dict[str, Any]]:
        if not os.path.exists(self.registry_path):
            return []
        with open(self.registry_path, encoding="utf-8") as f:
            try:
                data = yaml.safe_load(f)
                return data if isinstance(data, list) else []
            except Exception:
                return []

    def perform_audit(self) -> dict[str, Any]:
        raw_flags = self.load_raw_flags()

        # 1. Detect Duplicates
        duplicates = []
        seen_names = set()
        for flag in raw_flags:
            name = flag.get("name", "").upper()
            if not name:
                continue
            if name in seen_names:
                duplicates.append(name)
            seen_names.add(name)

        # 2. Scan for orphans using the registry service
        scan_results = self.registry_service.scan_orphans()
        orphans_list = scan_results.get("orphans", [])

        # Filter orphans to only include active/experimental flags that are unused
        registered_status = {
            f.get("name", "").upper(): f.get("status", "active").lower() for f in raw_flags
        }
        actual_orphans = [
            o
            for o in orphans_list
            if registered_status.get(o.upper(), "active") in ("active", "experimental")
        ]
        orphans_set = {o.upper() for o in actual_orphans}

        # 3. Detect Conflicts
        active_conflicts = self.registry_service.detect_active_conflicts()

        # Audit lists
        sem_docs = []
        sem_owner = []
        sem_safe_default_reason = []
        classified_flags = {
            "active": [],
            "experimental": [],
            "deprecated": [],
            "orphaned": [],
            "internal_only": [],
        }

        for flag in raw_flags:
            name = flag.get("name", "UNNAMED").upper()

            # Docs validation (description or safe_default_reason or registry rules)
            description = flag.get("description", "")
            if not description and not flag.get("safe_default_reason"):
                sem_docs.append(name)

            # Owner validation
            owner = flag.get("owner", "").strip()
            if not owner:
                sem_owner.append(name)

            # Safe default reason validation
            safe_reason = flag.get("safe_default_reason", "").strip()
            if not safe_reason:
                sem_safe_default_reason.append(name)

            # Classification rules:
            status = flag.get("status", "active").lower()

            if status == "deprecated":
                classified_flags["deprecated"].append(flag)
            elif status == "internal":
                classified_flags["internal_only"].append(flag)
            elif name in orphans_set:
                classified_flags["orphaned"].append(flag)
            elif status == "experimental":
                classified_flags["experimental"].append(flag)
            else:
                classified_flags["active"].append(flag)

        return {
            "total_registered": len(raw_flags),
            "duplicates": sorted(list(set(duplicates))),
            "orphans": sorted(actual_orphans),
            "active_conflicts": active_conflicts,
            "sem_docs": sorted(sem_docs),
            "sem_owner": sorted(sem_owner),
            "sem_safe_default_reason": sorted(sem_safe_default_reason),
            "classification": classified_flags,
        }

    def generate_report(self, audit_results: dict[str, Any]) -> str:
        report_dir = os.path.abspath(os.path.join(self.registry_path, "../../artifacts/platform"))
        os.makedirs(report_dir, exist_ok=True)
        report_path = os.path.join(report_dir, "feature-flag-audit.md")

        timestamp = datetime.now(UTC).isoformat()

        # Build Markdown content
        md = f"""# Feature Flag Governance Audit Report

Generated on: `{timestamp}`

## Classification Summary

| Classification | Count | Description |
| :--- | :---: | :--- |
| **Active** | {len(audit_results["classification"]["active"])} | Active flags currently used in the codebase/env. |
| **Experimental** | {len(audit_results["classification"]["experimental"])} | Opt-in features in experimental status. |
| **Deprecated** | {len(audit_results["classification"]["deprecated"])} | Marked for deprecation, awaiting cleanup. |
| **Orphaned** | {len(audit_results["classification"]["orphaned"])} | Registered flags with no references in code or .env.example. |
| **Internal Only** | {len(audit_results["classification"]["internal_only"])} | Internal environment-only control flags. |
| **Total** | {audit_results["total_registered"]} | Total flags defined in the registry. |

---

## Governance Violations

### 1. Duplicated Flags ({len(audit_results["duplicates"])})
"""
        if audit_results["duplicates"]:
            for d in audit_results["duplicates"]:
                md += f"- ❌ `{d}` (defined multiple times in yaml)\n"
        else:
            md += "- ✅ None\n"

        md += f"""
### 2. Missing Documentation ({len(audit_results["sem_docs"])})
Flags that lack a description or safe default explanation.
"""
        if audit_results["sem_docs"]:
            for d in audit_results["sem_docs"]:
                md += f"- ❌ `{d}`\n"
        else:
            md += "- ✅ None\n"

        md += f"""
### 3. Missing Owner ({len(audit_results["sem_owner"])})
Flags that do not declare an owner team or service path.
"""
        if audit_results["sem_owner"]:
            for o in audit_results["sem_owner"]:
                md += f"- ❌ `{o}`\n"
        else:
            md += "- ✅ None\n"

        md += f"""
### 4. Missing Safe Default Reason ({len(audit_results["sem_safe_default_reason"])})
"""
        if audit_results["sem_safe_default_reason"]:
            for r in audit_results["sem_safe_default_reason"]:
                md += f"- ❌ `{r}`\n"
        else:
            md += "- ✅ None\n"

        md += f"""
### 5. Active Conflicts ({len(audit_results["active_conflicts"])})
"""
        if audit_results["active_conflicts"]:
            for c in audit_results["active_conflicts"]:
                md += f"- ❌ `{c.get('flag_a')}` conflicts with `{c.get('flag_b')}`: {c.get('message')}\n"
        else:
            md += "- ✅ None\n"

        md += """
---

## Detailed Classification List

### Active Flags
"""
        for f in sorted(audit_results["classification"]["active"], key=lambda x: x.get("name", "")):
            md += f"- `{f.get('name')}` (Owner: `{f.get('owner')}`, Area: `{f.get('area')}`)\n"

        md += "\n### Experimental Flags\n"
        if audit_results["classification"]["experimental"]:
            for f in sorted(
                audit_results["classification"]["experimental"], key=lambda x: x.get("name", "")
            ):
                md += f"- `{f.get('name')}` (Owner: `{f.get('owner')}`)\n"
        else:
            md += "- None\n"

        md += "\n### Deprecated Flags\n"
        if audit_results["classification"]["deprecated"]:
            for f in sorted(
                audit_results["classification"]["deprecated"], key=lambda x: x.get("name", "")
            ):
                md += f"- `{f.get('name')}` (Replacement: `{f.get('replacement') or 'None'}`)\n"
        else:
            md += "- None\n"

        md += "\n### Orphaned Flags\n"
        if audit_results["classification"]["orphaned"]:
            for f in sorted(
                audit_results["classification"]["orphaned"], key=lambda x: x.get("name", "")
            ):
                md += f"- `{f.get('name')}` (Status: `{f.get('status')}`, Owner: `{f.get('owner')}`)\n"
        else:
            md += "- None\n"

        md += "\n### Internal Only Flags\n"
        if audit_results["classification"]["internal_only"]:
            for f in sorted(
                audit_results["classification"]["internal_only"], key=lambda x: x.get("name", "")
            ):
                md += f"- `{f.get('name')}` (Owner: `{f.get('owner')}`)\n"
        else:
            md += "- None\n"

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(md)

        return report_path

    def cleanup_orphaned_flags(self, mode: str = "deprecate") -> tuple[int, list[str]]:
        """
        Cleans up orphaned flags from the registry.
        mode can be:
            "remove": Delete the orphaned flags from yaml file.
            "deprecate": Set status of orphaned flags to "deprecated" (or "internal" if already internal).
        Returns:
            (count_updated, list_of_modified_flags)
        """
        raw_flags = self.load_raw_flags()
        audit_results = self.perform_audit()
        orphans = {o.upper() for o in audit_results["orphans"]}

        if not orphans:
            return 0, []

        updated_flags = []
        modified_list = []

        for flag in raw_flags:
            name = flag.get("name", "").upper()
            if name in orphans:
                modified_list.append(name)
                if mode == "remove":
                    # Skip writing this flag to updated list
                    continue
                elif mode == "deprecate":
                    flag["status"] = "deprecated"
                    # Add standard fields required for deprecated status
                    if "remove_after" not in flag:
                        flag["remove_after"] = "v2.2.0"
                    if "replacement" not in flag:
                        flag["replacement"] = ""
            updated_flags.append(flag)

        # Write back to yaml
        with open(self.registry_path, "w", encoding="utf-8") as f:
            yaml.dump(updated_flags, f, default_flow_style=False, sort_keys=False)

        return len(modified_list), sorted(modified_list)
