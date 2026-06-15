#!/usr/bin/env python3
"""Validate local Markdown links for canonical docs."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CANONICAL_FILES = [
    "README.md",
    "docs/index.md",
    "docs/CANONICAL_INDEX.md",
    "docs/quickstart.md",
    "docs/INSTALL.md",
    "docs/OPENAI_COMPATIBILITY.md",
    "docs/API_REFERENCE.md",
    "docs/CONFIGURATION_REFERENCE.md",
    "docs/FLAGS_INVENTORY.md",
    "docs/PRODUCT_SURFACE.md",
    "docs/platform/supported-surface.md",
    "docs/support/supported-surface-area.md",
    "docs/api/supported-api-surface.md",
    "docs/operations/platform_runbook.md",
    "docs/deployment/appliance-deploy.md",
    "docs/deployment/kubernetes-deploy.md",
    "docs/support/troubleshooting.md",
    "docs/support/support-bundle.md",
]
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def iter_markdown_files() -> list[Path]:
    return [REPO_ROOT / relative for relative in CANONICAL_FILES]


def resolve_target(source: Path, target: str) -> Path:
    cleaned = target.split("#", 1)[0].strip()
    return (source.parent / cleaned).resolve()


def main() -> int:
    errors: list[str] = []

    for doc in iter_markdown_files():
        content = doc.read_text(encoding="utf-8")
        for raw_target in LINK_RE.findall(content):
            target = raw_target.strip()
            if not target or target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            if target.startswith("file://"):
                errors.append(
                    f"{doc.relative_to(REPO_ROOT)}: forbidden absolute file link {target}"
                )
                continue
            resolved = resolve_target(doc, target)
            if not resolved.exists():
                errors.append(f"{doc.relative_to(REPO_ROOT)}: broken link {target}")

    if errors:
        print("Link check failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("OK: local markdown links resolved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
