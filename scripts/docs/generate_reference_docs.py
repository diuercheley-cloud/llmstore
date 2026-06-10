#!/usr/bin/env python3
"""Generate reference documentation from code and configuration."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
import sys
from typing import Any

import yaml
from pydantic_core import PydanticUndefined

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_ROOT = REPO_ROOT / "docs"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from control_plane.app.services.config_service import BaseAppConfig


GENERATED_FILES = {
    "api": DOCS_ROOT / "API_REFERENCE.md",
    "config": DOCS_ROOT / "CONFIGURATION_REFERENCE.md",
    "flags": DOCS_ROOT / "FLAGS_INVENTORY.md",
    "product": DOCS_ROOT / "PRODUCT_SURFACE.md",
}


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def render_link(raw: str | None, base: Path) -> str:
    if not raw:
        return "-"
    cleaned = raw.lstrip("/")
    if cleaned.startswith("docs/"):
        cleaned = cleaned[5:]
    target = DOCS_ROOT / cleaned
    if target.exists():
        relative = target.relative_to(base.parent).as_posix()
        return f"[{cleaned}]({relative})"
    return f"`{raw}`"


def md(value: Any) -> str:
    if value is None or value == "":
        return "-"
    if isinstance(value, bool):
        text = "true" if value else "false"
    elif isinstance(value, (list, tuple, set)):
        text = ", ".join(str(item) for item in value) if value else "-"
    else:
        text = str(value)
    return text.replace("|", "\\|").replace("\n", " ").strip()


def status_rank(value: str) -> tuple[int, str]:
    order = {
        "production_core": 0,
        "production_optional": 1,
        "beta": 2,
        "experimental": 3,
        "internal": 4,
        "deprecated": 5,
    }
    return (order.get(value, 99), value)


def render_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(md(cell) for cell in row) + " |")
    return "\n".join(lines)


def generate_api_reference() -> str:
    entries = load_yaml(REPO_ROOT / "config" / "api-surface.yaml")
    status_counts = Counter(entry["status"] for entry in entries)
    rows = []
    for entry in sorted(entries, key=lambda item: (item["status"], item["endpoint"], item["method"])):
        rows.append(
            [
                entry["endpoint"],
                entry["method"],
                entry["status"],
                entry.get("owner", "-"),
                entry.get("since_version", "-"),
                entry.get("replacement", "-"),
                render_link(entry.get("docs_url"), GENERATED_FILES["api"]),
            ]
        )

    summary_rows = [[status, count] for status, count in sorted(status_counts.items())]
    return f"""---
owner: platform-ops
status: reference-generated
generated_from:
  - config/api-surface.yaml
generated_by: scripts/docs/generate_reference_docs.py
---

# API Reference

This document is generated from `config/api-surface.yaml`. Update the YAML, then regenerate the docs.

## Status Summary

{render_table(["Status", "Endpoints"], summary_rows)}

## Endpoint Inventory

{render_table(["Endpoint", "Method", "Status", "Owner", "Since", "Replacement", "Docs"], rows)}
"""


def field_env_name(field_name: str, field_info: Any) -> str:
    alias = field_info.alias
    if alias:
        return str(alias)
    validation_alias = getattr(field_info, "validation_alias", None)
    if validation_alias:
        text = str(validation_alias)
        parts = [part for part in text.replace("AliasChoices", "").replace("(", "").replace(")", "").replace("'", "").split(",") if part.strip()]
        if parts:
            return parts[0].strip()
    return field_name.upper()


def classify_secret(name: str) -> bool:
    upper = name.upper()
    markers = ("TOKEN", "SECRET", "PASSWORD", "KEY", "DSN")
    return any(marker in upper for marker in markers)


def normalize_default(value: Any, secret: bool) -> str:
    if value is PydanticUndefined:
        return "required"
    if secret and value not in ("", None, False):
        return "<redacted>"
    if secret and value in ("", None):
        return "<empty>"
    return md(value)


def type_name(annotation: Any) -> str:
    text = str(annotation)
    for prefix in ("<class '", "typing.", "class "):
        text = text.replace(prefix, "")
    return text.replace("'>", "").replace("NoneType", "None")


def group_name(field_name: str, env_name: str) -> str:
    token = (env_name or field_name).split("_", 1)[0].lower()
    return token


def generate_configuration_reference() -> str:
    grouped: dict[str, list[list[str]]] = defaultdict(list)

    for field_name, field_info in sorted(BaseAppConfig.model_fields.items()):
        env_name = field_env_name(field_name, field_info)
        secret = classify_secret(env_name) or classify_secret(field_name)
        grouped[group_name(field_name, env_name)].append(
            [
                env_name,
                field_name,
                type_name(field_info.annotation),
                normalize_default(field_info.default, secret),
                "yes" if secret else "no",
            ]
        )

    sections = []
    for group in sorted(grouped):
        sections.append(f"## `{group}`")
        sections.append("")
        sections.append(
            render_table(
                ["Env", "Field", "Type", "Default", "Secret"],
                grouped[group],
            )
        )
        sections.append("")

    return f"""---
owner: platform-ops
status: reference-generated
generated_from:
  - control_plane.app.services.config_service.BaseAppConfig
generated_by: scripts/docs/generate_reference_docs.py
---

# Configuration Reference

This document is generated from `BaseAppConfig`. Required values are marked as `required`.

{chr(10).join(sections).rstrip()}
"""


def generate_flags_inventory() -> str:
    flags = load_yaml(REPO_ROOT / "config" / "feature-flags.yaml")
    field_map = BaseAppConfig.model_fields
    rows = []

    for flag in sorted(flags, key=lambda item: item["name"]):
        field_name = None
        for candidate, field_info in field_map.items():
            env_name = field_env_name(candidate, field_info)
            if env_name == flag["name"]:
                field_name = candidate
                break
        rows.append(
            [
                flag["name"],
                field_name or "-",
                flag.get("default", "-"),
                flag.get("status", "-"),
                flag.get("owner", "-"),
                flag.get("risk_level", "-"),
                flag.get("dependencies", []),
                flag.get("conflicts", []),
            ]
        )

    return f"""---
owner: platform-ops
status: reference-generated
generated_from:
  - config/feature-flags.yaml
  - control_plane.app.services.config_service.BaseAppConfig
generated_by: scripts/docs/generate_reference_docs.py
---

# Flags Inventory

This document is generated from the feature flag registry and the runtime settings model.

{render_table(["Flag", "Field", "Default", "Status", "Owner", "Risk", "Dependencies", "Conflicts"], rows)}
"""


def capability_surface(capability: dict[str, Any]) -> str:
    api_prefix = capability.get("api_prefix")
    flag = capability.get("feature_flag")
    if api_prefix and flag:
        return f"`{api_prefix}` / `{flag}`"
    if api_prefix:
        return f"`{api_prefix}`"
    if flag:
        return f"`{flag}`"
    return "-"


def generate_product_surface() -> str:
    payload = load_yaml(REPO_ROOT / "config" / "supported-surface.yaml")
    capabilities = payload["capabilities"]
    observed_statuses = {item["status"] for item in capabilities}
    summary_rows = [
        [status, count]
        for status, count in sorted(Counter(item["status"] for item in capabilities).items(), key=lambda item: status_rank(item[0]))
    ]

    rows = []
    for capability in sorted(capabilities, key=lambda item: (status_rank(item["status"]), item["name"].lower())):
        rows.append(
            [
                capability["name"],
                capability["id"],
                capability["status"],
                capability.get("support_level", "-"),
                capability.get("owner", "-"),
                capability_surface(capability),
                render_link(capability.get("docs_url"), GENERATED_FILES["product"]),
                capability.get("limitations", "-"),
            ]
        )

    tiers = payload.get("tiers", {})
    tier_rows = [[name, description] for name, description in tiers.items()]
    fallback_definitions = {
        "advisory": "Implemented as advisory-only posture; not a production claim.",
        "non-production": "Available for development or transition use only; not a supported production posture.",
    }
    for status in sorted(observed_statuses):
        if status not in tiers and status in fallback_definitions:
            tier_rows.append([status, fallback_definitions[status]])

    return f"""---
owner: platform-ops
status: reference-generated
generated_from:
  - config/supported-surface.yaml
generated_by: scripts/docs/generate_reference_docs.py
---

# Product Surface

This document is generated from `config/supported-surface.yaml`. It is the documentation source of truth for capability status claims.

## Lifecycle Tiers

{render_table(["Tier", "Definition"], tier_rows)}

## Status Summary

{render_table(["Status", "Capabilities"], summary_rows)}

## Capability Matrix

{render_table(["Capability", "ID", "Status", "Support", "Owner", "Surface", "Docs", "Limitations"], rows)}
"""


def generate_all() -> dict[Path, str]:
    return {
        GENERATED_FILES["api"]: generate_api_reference(),
        GENERATED_FILES["config"]: generate_configuration_reference(),
        GENERATED_FILES["flags"]: generate_flags_inventory(),
        GENERATED_FILES["product"]: generate_product_surface(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Fail if generated docs are out of date.")
    args = parser.parse_args()

    rendered = generate_all()
    mismatches: list[Path] = []

    for path, content in rendered.items():
        normalized = content.rstrip() + "\n"
        if args.check:
            current = path.read_text(encoding="utf-8") if path.exists() else ""
            if current != normalized:
                mismatches.append(path)
            continue
        path.write_text(normalized, encoding="utf-8")

    if mismatches:
        for path in mismatches:
            print(f"OUTDATED: {path.relative_to(REPO_ROOT)}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
