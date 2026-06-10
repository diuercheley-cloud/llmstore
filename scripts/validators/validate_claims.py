#!/usr/bin/env python3
"""Validate repository text for prohibited security and certification claims."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

SCAN_TARGETS = (
    REPO_ROOT / "docs",
    REPO_ROOT / "README.md",
    REPO_ROOT / "app" / "static",
    REPO_ROOT / "control_plane" / "app" / "static",
    REPO_ROOT / "scripts",
)

PROHIBITED_CLAIMS = (
    "military-grade",
    "unbreakable",
    "formally certified",
    "guaranteed secure",
    "real hardware attestation",
    "government certified",
    "certified soc2",
    "certified fedramp",
    "certified confidential computing",
)

ALLOW_CONTEXT_MARKERS = (
    "does not claim",
    "does not provide",
    "placeholder",
    "not certified",
    "placeholder_attestation",
    "soc2-style",
    "limitations",
    "prohibited claim",
    "prohibited claims",
    "prohibited_claims",
    "claims proibidas",
    "must not appear",
    "nao devem aparecer",
    "claims policy",
)

EXCLUDED_PATHS = {
    REPO_ROOT / "scripts" / "validate_claims.py",
}

TEXT_EXTENSIONS = {
    ".md",
    ".txt",
    ".html",
    ".htm",
    ".js",
    ".json",
    ".py",
    ".sh",
    ".css",
    ".yml",
    ".yaml",
    ".svg",
    ".xml",
}

CONTEXT_WINDOW = 300


def iter_scan_files() -> list[Path]:
    """Collect repository files that should be scanned."""

    files: list[Path] = []
    for target in SCAN_TARGETS:
        if not target.exists():
            continue
        if target.is_file():
            if target not in EXCLUDED_PATHS:
                files.append(target)
            continue
        for path in sorted(target.rglob("*")):
            if path.is_dir() or path in EXCLUDED_PATHS:
                continue
            if path.suffix.lower() in TEXT_EXTENSIONS:
                files.append(path)
    return files


def read_text_safely(path: Path) -> str | None:
    """Read text content, skipping binary or undecodable files."""

    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def _has_allowed_context(content_lower: str, index: int, claim: str) -> bool:
    start = max(0, index - CONTEXT_WINDOW)
    end = min(len(content_lower), index + len(claim) + CONTEXT_WINDOW)
    window = content_lower[start:end]
    return any(marker in window for marker in ALLOW_CONTEXT_MARKERS)


def find_claim_violations_in_text(content: str, path: Path) -> list[dict[str, str]]:
    """Find prohibited claims that are not clearly negated or marked as placeholders."""

    content_lower = content.lower()
    violations: list[dict[str, str]] = []
    for claim in PROHIBITED_CLAIMS:
        search_from = 0
        while True:
            index = content_lower.find(claim, search_from)
            if index == -1:
                break
            if not _has_allowed_context(content_lower, index, claim):
                line_number = content[:index].count("\n") + 1
                violations.append(
                    {
                        "path": str(path.relative_to(REPO_ROOT)),
                        "issue": f"prohibited claim without allowed context: {claim}",
                        "line": str(line_number),
                    }
                )
            search_from = index + len(claim)
    return violations


def validate_claims() -> list[dict[str, str]]:
    """Scan configured repository paths for prohibited claims."""

    failures: list[dict[str, str]] = []
    for path in iter_scan_files():
        content = read_text_safely(path)
        if content is None:
            continue
        failures.extend(find_claim_violations_in_text(content, path))
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit failures as JSON.")
    args = parser.parse_args()

    failures = validate_claims()
    if args.json:
        print(json.dumps(failures, indent=2, sort_keys=True))
    elif failures:
        print("Claims validation failed:")
        for failure in failures:
            print(f"- {failure['path']}:{failure['line']}: {failure['issue']}")
    else:
        print("Claims validation passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
