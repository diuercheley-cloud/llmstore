#!/usr/bin/env python3
"""Generate the MkDocs portal from curated source docs and generated references."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Iterable
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_ROOT = REPO_ROOT / "docs"
PORTAL_ROOT = REPO_ROOT / "docs-site" / "docs"
REFERENCE_ROOT = PORTAL_ROOT / "reference"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.docs.generate_reference_docs import generate_all

SYNC_MAP = {
    PORTAL_ROOT / "getting-started" / "quickstart.md": DOCS_ROOT / "quickstart.md",
    PORTAL_ROOT / "getting-started" / "installation.md": DOCS_ROOT / "INSTALL.md",
    PORTAL_ROOT / "getting-started" / "install-wizard.md": DOCS_ROOT / "INSTALL_WIZARD.md",
    PORTAL_ROOT / "getting-started" / "operational-profiles.md": DOCS_ROOT / "PROFILES.md",
    PORTAL_ROOT / "architecture" / "platform-overview.md": DOCS_ROOT
    / "architecture"
    / "platform_overview.md",
    PORTAL_ROOT / "architecture" / "domain-map.md": DOCS_ROOT
    / "architecture"
    / "platform_domain_map.md",
    PORTAL_ROOT / "agents" / "agent-runtime.md": DOCS_ROOT / "agents" / "agent-runtime.md",
    PORTAL_ROOT / "agents" / "tool-execution.md": DOCS_ROOT / "agents" / "tool-execution.md",
    PORTAL_ROOT / "rag" / "knowledge-base-ingestion.md": DOCS_ROOT
    / "rag"
    / "knowledge-base-ingestion.md",
    PORTAL_ROOT / "rag" / "vector-db-providers.md": DOCS_ROOT / "rag" / "vector-db-providers.md",
    PORTAL_ROOT / "security" / "admin-rbac.md": DOCS_ROOT / "security" / "admin-rbac.md",
    PORTAL_ROOT / "security" / "agent-spend-controls.md": DOCS_ROOT
    / "security"
    / "agent-spend-controls.md",
    PORTAL_ROOT / "governance" / "data-governance.md": DOCS_ROOT
    / "governance"
    / "data_governance.md",
    PORTAL_ROOT / "governance" / "supply-chain-governance.md": DOCS_ROOT
    / "governance"
    / "supply_chain_governance.md",
    PORTAL_ROOT / "operations" / "platform-runbook.md": DOCS_ROOT
    / "operations"
    / "platform_runbook.md",
    PORTAL_ROOT / "operations" / "profile-selection.md": DOCS_ROOT
    / "operations"
    / "profile-selection.md",
    PORTAL_ROOT / "api" / "supported-surface.md": DOCS_ROOT / "api" / "supported-api-surface.md",
    PORTAL_ROOT / "releases" / "latest-release-notes.md": DOCS_ROOT
    / "releases"
    / "latest_release_notes.md",
    PORTAL_ROOT / "releases" / "release-process.md": DOCS_ROOT / "releases" / "release_process.md",
}

REFERENCE_MAP = {
    REFERENCE_ROOT / "api-reference.md": DOCS_ROOT / "API_REFERENCE.md",
    REFERENCE_ROOT / "configuration-reference.md": DOCS_ROOT / "CONFIGURATION_REFERENCE.md",
    REFERENCE_ROOT / "feature-flags.md": DOCS_ROOT / "FLAGS_INVENTORY.md",
    REFERENCE_ROOT / "product-surface.md": DOCS_ROOT / "PRODUCT_SURFACE.md",
}

MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[(?P<label>[^\]]+)\]\((?P<href>[^)]+)\)")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def source_to_portal_map() -> dict[Path, Path]:
    mapping: dict[Path, Path] = {}
    for portal_path, source_path in {**SYNC_MAP, **REFERENCE_MAP}.items():
        mapping[source_path.resolve()] = portal_path.resolve()
    return mapping


def downgrade_link(label: str, href: str) -> str:
    normalized_label = label.strip()
    normalized_href = href.strip()
    if normalized_label == normalized_href:
        return f"`{normalized_label}`"
    return f"{normalized_label} (`{normalized_href}`)"


def rewrite_links(body: str, source: Path, target: Path) -> str:
    portal_map = source_to_portal_map()

    def replace(match: re.Match[str]) -> str:
        label = match.group("label")
        href = match.group("href").strip()
        href_path, anchor = href.split("#", 1) if "#" in href else (href, "")

        if href_path.startswith(("http://", "https://", "mailto:", "tel:")) or href.startswith("#"):
            return match.group(0)

        resolved = (source.parent / href_path).resolve()
        portal_target = portal_map.get(resolved)
        if portal_target is None:
            return downgrade_link(label, href)

        relative_target = os.path.relpath(portal_target, target.parent).replace(os.sep, "/")
        if anchor:
            relative_target = f"{relative_target}#{anchor}"
        return f"[{label}]({relative_target})"

    return MARKDOWN_LINK_RE.sub(replace, body)


def sync_doc(target: Path, source: Path) -> str:
    body = source.read_text(encoding="utf-8").rstrip()
    body = rewrite_links(body, source, target)
    source_rel = source.relative_to(REPO_ROOT).as_posix()
    return f"<!-- synced_from: {source_rel} -->\n\n> Source of truth: `{source_rel}`\n\n{body}\n"


def generate_profiles_reference() -> str:
    profile_dir = REPO_ROOT / "config" / "profiles"
    profiles: list[dict[str, object]] = []

    for path in sorted(profile_dir.glob("*.yaml")):
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            continue
        if "name" not in payload or "settings" not in payload or "features" not in payload:
            continue
        profiles.append(
            {
                "name": payload["name"],
                "description": payload.get("description", ""),
                "settings": payload.get("settings", {}),
                "features": payload.get("features", {}),
                "path": path.relative_to(REPO_ROOT).as_posix(),
            }
        )

    summary_lines = [
        "| Profile | Description | Enabled Features |",
        "| --- | --- | --- |",
    ]
    for profile in profiles:
        enabled = sorted(name for name, enabled in profile["features"].items() if enabled is True)
        summary_lines.append(
            f"| `{profile['name']}` | {profile['description']} | {', '.join(enabled) or '-'} |"
        )

    detail_sections: list[str] = []
    for profile in profiles:
        settings = "\n".join(
            f"- `{key}` = `{value}`" for key, value in sorted(profile["settings"].items())
        )
        features = "\n".join(
            f"- `{key}`: `{'enabled' if value else 'disabled'}`"
            for key, value in sorted(profile["features"].items())
        )
        detail_sections.append(
            f"## `{profile['name']}`\n\n"
            f"Source: `{profile['path']}`\n\n"
            f"{profile['description']}\n\n"
            f"### Settings\n\n{settings or '-'}\n\n"
            f"### Feature Matrix\n\n{features or '-'}\n"
        )

    return (
        "---\n"
        "owner: platform-ops\n"
        "status: reference-generated\n"
        "generated_from:\n"
        "  - config/profiles/*.yaml\n"
        "generated_by: scripts/docs/generate_docs_site.py\n"
        "---\n\n"
        "# Profiles Reference\n\n"
        "This page is generated from the official operational profile manifests.\n\n"
        "## Summary\n\n" + "\n".join(summary_lines) + "\n\n" + "\n\n".join(detail_sections)
    )


def generate_release_manifest_page() -> str:
    manifest_path = DOCS_ROOT / "releases" / "latest_release_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    pretty = json.dumps(manifest, indent=2, ensure_ascii=True)
    return (
        "---\n"
        "owner: platform-ops\n"
        "status: reference-generated\n"
        "generated_from:\n"
        "  - docs/releases/latest_release_manifest.json\n"
        "generated_by: scripts/docs/generate_docs_site.py\n"
        "---\n\n"
        "# Latest Release Manifest\n\n"
        "```json\n"
        f"{pretty}\n"
        "```\n"
    )


def render_outputs() -> dict[Path, str]:
    outputs: dict[Path, str] = {}

    # Keep the root generated references fresh before syncing them into the portal.
    for path, content in generate_all().items():
        write_text(path, content)

    for target, source in SYNC_MAP.items():
        outputs[target] = sync_doc(target, source)

    for target, source in REFERENCE_MAP.items():
        outputs[target] = sync_doc(target, source)

    outputs[REFERENCE_ROOT / "profiles.md"] = generate_profiles_reference()
    outputs[PORTAL_ROOT / "releases" / "latest-release-manifest.md"] = (
        generate_release_manifest_page()
    )

    return outputs


def iter_mismatches(rendered: dict[Path, str]) -> Iterable[Path]:
    for path, content in rendered.items():
        current = path.read_text(encoding="utf-8") if path.exists() else ""
        if current != content.rstrip() + "\n":
            yield path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check", action="store_true", help="Fail if the generated portal is out of date."
    )
    args = parser.parse_args()

    rendered = render_outputs()

    if args.check:
        mismatches = list(iter_mismatches(rendered))
        for path in mismatches:
            print(f"OUTDATED: {path.relative_to(REPO_ROOT)}")
        return 1 if mismatches else 0

    for path, content in rendered.items():
        write_text(path, content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
