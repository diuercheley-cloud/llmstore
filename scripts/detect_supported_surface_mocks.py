#! /usr/bin/env python3
"""
Detect mocks, placeholders, simulated data, and fake responses in supported/core
endpoints.  Fails if a route classified as "supported" or "core" in
generated/route_surface_manifest.json contains such patterns without an explicit
exemption in governance/mock_exceptions.yml, a dry_run gate, a simulated-status
guard, an experimental feature flag, or a test covering the fallback path.

Usage:
    python3 scripts/detect_supported_surface_mocks.py

Exit codes:
    0   All supported/core endpoints are clean or properly exempted.
    1   Violations found.
"""

from __future__ import annotations

import ast
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent

ROUTE_MANIFEST = REPO_ROOT / "generated" / "route_surface_manifest.json"
MOCK_EXCEPTIONS = REPO_ROOT / "governance" / "mock_exceptions.yml"

# Patterns that indicate a mock/placeholder/simulated/fake implementation.
# Each pattern is (regex, severity, description).
PATTERNS: list[tuple[str, str, str]] = [
    # -- explicit mocks
    (r'\bmock\b', "high", "literal 'mock' reference"),
    # -- placeholder sentinels
    (r'\bplaceholder\b', "high", "literal 'placeholder' reference"),
    # -- simulated paths
    (r'\bsimulated\b', "high", "literal 'simulated' reference"),
    # -- fake data generators
    (r'\bfake\b', "medium", "literal 'fake' reference"),
    # -- TODO comments in function bodies (not docstrings)
    (r'^\s*#\s*TODO\b', "low", "inline TODO comment"),
    # -- hardcoded 200 OK without real logic (minimal stub endpoints)
    (r'return\s+{\s*["\']status["\']\s*:\s*["\']ok["\']?\s*}', "medium",
     "hardcoded status-ok stub"),
    # -- pass-only function bodies (empty endpoint stubs)
    (r'def\s+\w+\(.*\):\s*\n\s+(\.{3}|pass)\s*$', "medium",
     "stub function (pass / ...)"),
]

# Patterns that, if present in the same file, exempt a match from violation.
EXEMPTION_PATTERNS: list[str] = [
    r'\bdry_run\b',
    r'\bdryrun\b',
    r'\bsimulated\s*(status|mode|provider)\b',
    r'\bexperimental\b',
    r'\bfeature_flag\b',
    r'\bDEMO_MODE\b',
    r'\bMOCK_EMBEDDINGS\b',
    r'\bPAYMENT_MODE\b',
    r'\bCHAOS_ENABLED\b',
    r'\bIS_TESTING\b',
    r'\bTESTING\b',
    r'\bsandbox\b',
]


def load_manifest() -> list[dict[str, Any]]:
    if not ROUTE_MANIFEST.exists():
        print(f"ERROR: route manifest not found at {ROUTE_MANIFEST}", file=sys.stderr)
        print("Run 'make generate-route-surface' first.", file=sys.stderr)
        sys.exit(1)
    return json.loads(ROUTE_MANIFEST.read_text(encoding="utf-8"))


def load_exceptions() -> dict[str, dict[str, Any]]:
    if not MOCK_EXCEPTIONS.exists():
        return {}
    data = yaml.safe_load(MOCK_EXCEPTIONS.read_text(encoding="utf-8")) or {}
    exc = {}
    for e in data.get("exceptions", []):
        exc[e["file"]] = e
    return exc


def module_to_path(module: str) -> Path:
    """Convert 'app.api.abuse_admin' to 'control_plane/app/api/abuse_admin.py'."""
    rel = module.replace(".", "/") + ".py"
    return REPO_ROOT / rel


def resolve_service_files(api_file: Path) -> list[Path]:
    """Find imported service files by parsing import statements."""
    services: list[Path] = []
    try:
        tree = ast.parse(api_file.read_text(encoding="utf-8"))
    except (SyntaxError, FileNotFoundError):
        return services
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod.startswith("app.services"):
                parts = mod.split(".")
                rel = "/".join(parts) + ".py"
                sp = REPO_ROOT / "control_plane" / rel
                if sp.exists() and sp not in services:
                    services.append(sp)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("app.services"):
                    parts = alias.name.split(".")
                    rel = "/".join(parts) + ".py"
                    sp = REPO_ROOT / "control_plane" / rel
                    if sp.exists() and sp not in services:
                        services.append(sp)
    return services


def has_exemption_in_file(content: str, exceptions: dict[str, dict[str, Any]],
                          file_rel: str) -> tuple[bool, str]:
    """Check if a file is exempted either via global exception list or inline patterns."""
    # 1. Check governance exceptions
    if file_rel in exceptions:
        return True, f"exempted in mock_exceptions.yml ({exceptions[file_rel]['reason']})"

    # 2. Check inline exemption patterns
    for pat in EXEMPTION_PATTERNS:
        if re.search(pat, content, re.IGNORECASE):
            return True, f"inline exemption matched: /{pat}/"

    return False, ""


def has_test_coverage(route_path: str) -> bool:
    """Crude heuristic: checks whether the route path is referenced in test files."""
    tests_root = REPO_ROOT / "tests"
    if not tests_root.exists():
        return False
    result = os.popen(
        f"grep -rl --include='*.py' '{re.escape(route_path)}' {tests_root} 2>/dev/null | head -1"
    ).read().strip()
    return bool(result)


def scan_file(file_path: Path, file_rel: str, exceptions: dict,
              exempt_files: set[str]) -> list[dict[str, Any]]:
    """Scan a single file for mock patterns and return violations."""
    violations: list[dict[str, Any]] = []
    try:
        content = file_path.read_text(encoding="utf-8")
    except (FileNotFoundError, UnicodeDecodeError):
        return violations

    # Quick global exemption check
    is_exempt, exempt_reason = has_exemption_in_file(content, exceptions, file_rel)
    if is_exempt:
        exempt_files.add(file_rel)
        return violations

    lines = content.split("\n")
    for pattern, severity, desc in PATTERNS:
        for lineno, line in enumerate(lines, 1):
            if re.search(pattern, line, re.IGNORECASE):
                # Skip matches in comments if the pattern is about TODO
                stripped = line.strip()
                if pattern == r'^\s*#\s*TODO\b':
                    # Already only matches TODO comments, keep it
                    pass
                elif stripped.startswith("#") and pattern != r'^\s*#\s*TODO\b':
                    continue
                violations.append({
                    "file": file_rel,
                    "line": lineno,
                    "pattern": pattern,
                    "severity": severity,
                    "description": desc,
                    "code": line.strip()[:120],
                })

    return violations


def validate():
    manifest = load_manifest()
    exceptions = load_exceptions()

    # Group supported/core routes by router module
    module_routes: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for route in manifest:
        if route["status"] in ("supported", "core"):
            module_routes[route["router_module"]].append(route)

    exempt_files: set[str] = set()
    all_violations: list[dict[str, Any]] = []

    for module, routes in sorted(module_routes.items()):
        api_file = module_to_path(module)
        if not api_file.exists():
            continue

        file_rel = str(api_file.relative_to(REPO_ROOT))
        violations = scan_file(api_file, file_rel, exceptions, exempt_files)

        # Also scan imported service files
        for svc in resolve_service_files(api_file):
            svc_rel = str(svc.relative_to(REPO_ROOT))
            if svc_rel != file_rel:
                violations.extend(
                    scan_file(svc, svc_rel, exceptions, exempt_files)
                )

        # If violations exist, check route-level exemptions
        for v in violations:
            # Check if any route in this module has test coverage
            route_has_tests = any(
                has_test_coverage(r["path"]) for r in routes
            )
            if route_has_tests:
                continue  # exempt: tested fallback

            all_violations.append(v)

    # Deduplicate violations
    seen: set[tuple[str, int, str]] = set()
    unique_violations = []
    for v in all_violations:
        key = (v["file"], v["line"], v["pattern"])
        if key not in seen:
            seen.add(key)
            unique_violations.append(v)

    # Report
    if unique_violations:
        print(f"Found {len(unique_violations)} mock/placeholder violation(s) in "
              f"supported/core endpoints:\n")
        # Group by file
        by_file: dict[str, list[dict]] = defaultdict(list)
        for v in unique_violations:
            by_file[v["file"]].append(v)

        for fname, vlist in sorted(by_file.items()):
            print(f"  {fname} ({len(vlist)} match(es))")
            for v in vlist[:10]:
                sev = f"[{v['severity'].upper()}]" if v['severity'] != 'medium' else ""
                print(f"    L{v['line']}: {sev} {v['description']}")
                print(f"       code: {v['code']}")
            if len(vlist) > 10:
                print(f"    ... and {len(vlist) - 10} more")
            print()

        print("Remediation options:")
        print("  1. Remove mock/placeholder from supported/core endpoint")
        print("  2. Gate behind feature flag (experimental)")
        print("  3. Add dry_run query param guard")
        print("  4. Add simulated status routing")
        print("  5. Add test covering the fallback path")
        print("  6. Add exemption to governance/mock_exceptions.yml")
        print()
        sys.exit(1)
    else:
        if exempt_files:
            print(f"All supported/core endpoints clean ({len(exempt_files)} exempted files).")
        else:
            print("All supported/core endpoints clean.")
        sys.exit(0)


if __name__ == "__main__":
    validate()
