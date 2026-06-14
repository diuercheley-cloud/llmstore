#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
ADMIN_ROOT = REPO_ROOT / "frontend" / "admin" / "src"
CLIENT_ROOT = REPO_ROOT / "frontend" / "client" / "src"
EXCEPTIONS_FILE = REPO_ROOT / "governance" / "frontend_mock_exceptions.yml"

IMPORT_RE = re.compile(
    r"""(?:import|export)\s+(?:type\s+)?(?:[\w*\s{},]+?\s+from\s+)?["']([^"']+)["']""",
    re.MULTILINE,
)
ADMIN_DYNAMIC_IMPORT_RE = re.compile(r"import\(['\"](\.\.?/[^'\"]+)['\"]\)")
CLIENT_COMPONENT_RE = re.compile(r"<([A-Z][A-Za-z0-9_]*)\b")
CLIENT_IMPORT_RE = re.compile(r"""import\s+{?\s*([^}]+?)\s*}?\s+from\s+["'](\.\.?/[^"']+)["']""")

KEYWORD_PATTERNS = [
    re.compile(r"\bmock(?:ed|ing)?\b", re.IGNORECASE),
    re.compile(r"\bstatic data\b", re.IGNORECASE),
    re.compile(r"\bdemo data\b", re.IGNORECASE),
]

TOP_LEVEL_ARRAY_RE = re.compile(
    r"""(?m)^(?P<indent>\s*)(?:const|let|var)\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*(?::[^=]+)?=\s*\["""
)
STATE_ARRAY_RE = re.compile(
    r"""(?m)^(?P<indent>\s*)const\s+\[\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)[^\]]*\]\s*=\s*useState\(\s*\["""
)

SAFE_ARRAY_NAMES = {
    "navitems",
    "navconfig",
    "columns",
    "filterconfig",
    "batchactions",
    "tabs",
    "steps",
    "categories",
    "order",
    "shortcuts",
    "nodetypes",
    "node_types",
    "componentmap",
    "routes",
    "groups",
    "breadcrumbs",
    "cards",
    "includedcomponents",
    "excludedcomponents",
}
SUSPICIOUS_ARRAY_NAMES = {
    "runs",
    "disputes",
    "webhooks",
    "approvals",
    "evals",
    "bundles",
    "tools",
    "policies",
    "memoryitems",
    "messages",
}
ALLOWED_PATH_PARTS = ("/tests/", "/test/", "/stories/", "/fixtures/", "/demo/")
ALLOWED_SUFFIXES = (".test.ts", ".test.tsx", ".stories.ts", ".stories.tsx")


@dataclass
class Violation:
    path: str
    line: int
    rule: str
    detail: str


def load_exceptions() -> dict[str, str]:
    if not EXCEPTIONS_FILE.exists():
        return {}
    data = yaml.safe_load(EXCEPTIONS_FILE.read_text(encoding="utf-8")) or {}
    exceptions: dict[str, str] = {}
    for item in data.get("exceptions", []):
        file_path = item.get("file")
        reason = item.get("reason", "no reason provided")
        if file_path:
            exceptions[file_path] = reason
    return exceptions


def is_allowed_path(path: Path) -> bool:
    rel = "/" + str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    if rel.endswith(ALLOWED_SUFFIXES):
        return True
    return any(part in rel for part in ALLOWED_PATH_PARTS)


def resolve_relative_import(base: Path, target: str) -> Path | None:
    if not target.startswith("."):
        return None
    candidate = (base.parent / target).resolve()
    for option in (
        candidate,
        candidate.with_suffix(".ts"),
        candidate.with_suffix(".tsx"),
        candidate / "index.ts",
        candidate / "index.tsx",
    ):
        if option.exists():
            return option
    return None


def collect_graph(entrypoints: list[Path], extra_import_resolver=None) -> set[Path]:
    seen: set[Path] = set()
    stack = [path.resolve() for path in entrypoints if path.exists()]

    while stack:
        current = stack.pop()
        if current in seen or not current.exists():
            continue
        seen.add(current)

        content = current.read_text(encoding="utf-8")
        imports = [m.group(1) for m in IMPORT_RE.finditer(content)]
        if extra_import_resolver:
            imports.extend(extra_import_resolver(current, content))

        for target in imports:
            resolved = resolve_relative_import(current, target)
            if resolved and resolved not in seen:
                stack.append(resolved)

    return seen


def admin_entrypoints() -> list[Path]:
    routes_file = ADMIN_ROOT / "routes" / "adminRoutes.tsx"
    content = routes_file.read_text(encoding="utf-8")
    targets = [resolve_relative_import(routes_file, m.group(1)) for m in ADMIN_DYNAMIC_IMPORT_RE.finditer(content)]
    return [routes_file, *[t for t in targets if t is not None]]


def client_extra_imports(current: Path, content: str) -> list[str]:
    if current != CLIENT_ROOT / "App.tsx":
        return []

    imported_names: dict[str, str] = {}
    for match in CLIENT_IMPORT_RE.finditer(content):
        raw_names, import_path = match.groups()
        for name in [item.strip() for item in raw_names.split(",")]:
            if name:
                imported_names[name] = import_path

    used_components = set(CLIENT_COMPONENT_RE.findall(content))
    targets = []
    for component in used_components:
        import_path = imported_names.get(component)
        if import_path:
            targets.append(import_path)
    return targets


def should_ignore_keyword_line(line: str) -> bool:
    stripped = line.strip()
    if stripped.startswith("//") or stripped.startswith("*") or stripped.startswith("/*"):
        return True
    if stripped.startswith("{/*"):
        return True
    if "simulate incidents" in stripped.lower():
        return True
    return False


def find_line_number(content: str, offset: int) -> int:
    return content.count("\n", 0, offset) + 1


def scan_keywords(path: Path, content: str) -> list[Violation]:
    violations: list[Violation] = []
    for lineno, line in enumerate(content.splitlines(), start=1):
        if should_ignore_keyword_line(line):
            continue
        for pattern in KEYWORD_PATTERNS:
            match = pattern.search(line)
            if match:
                violations.append(
                    Violation(
                        path=str(path.relative_to(REPO_ROOT)),
                        line=lineno,
                        rule="keyword",
                        detail=f"keyword '{match.group(0)}' in official frontend surface",
                    )
                )
    return violations


def looks_like_data_array(name: str, block: str) -> bool:
    normalized = name.lower()
    if normalized in SAFE_ARRAY_NAMES:
        return False
    if normalized in SUSPICIOUS_ARRAY_NAMES:
        return True
    object_entries = block.count("{")
    numeric_values = len(re.findall(r"""['"]\d|:\s*['"]?\d""", block))
    return object_entries >= 2 and numeric_values >= 1


def extract_array_block(content: str, start: int) -> str:
    depth = 0
    started = False
    chars: list[str] = []
    for ch in content[start:]:
        chars.append(ch)
        if ch == "[":
            depth += 1
            started = True
        elif ch == "]" and started:
            depth -= 1
            if depth == 0:
                break
    return "".join(chars)


def scan_arrays(path: Path, content: str) -> list[Violation]:
    violations: list[Violation] = []
    for pattern in (TOP_LEVEL_ARRAY_RE, STATE_ARRAY_RE):
        for match in pattern.finditer(content):
            indent = match.group("indent") or ""
            if len(indent) > 2:
                continue
            name = match.group("name")
            block = extract_array_block(content, match.end() - 1)
            if looks_like_data_array(name, block):
                violations.append(
                    Violation(
                        path=str(path.relative_to(REPO_ROOT)),
                        line=find_line_number(content, match.start()),
                        rule="hardcoded_array",
                        detail=f"hardcoded data array '{name}' in official frontend surface",
                    )
                )
    return violations


def collect_official_files() -> set[Path]:
    admin_files = collect_graph(admin_entrypoints())
    client_files = collect_graph([CLIENT_ROOT / "App.tsx"], extra_import_resolver=client_extra_imports)
    return {path for path in admin_files | client_files if path.suffix in {".ts", ".tsx"}}


def main() -> int:
    exceptions = load_exceptions()
    official_files = sorted(collect_official_files())
    violations: list[Violation] = []

    for path in official_files:
        rel = str(path.relative_to(REPO_ROOT))
        if is_allowed_path(path) or rel in exceptions:
            continue

        content = path.read_text(encoding="utf-8")
        violations.extend(scan_keywords(path, content))
        violations.extend(scan_arrays(path, content))

    unique: dict[tuple[str, int, str], Violation] = {}
    for violation in violations:
        unique[(violation.path, violation.line, violation.detail)] = violation

    if unique:
        print("Frontend mock detection failed.\n")
        for violation in sorted(unique.values(), key=lambda item: (item.path, item.line, item.detail)):
            print(f"- {violation.path}:{violation.line} [{violation.rule}] {violation.detail}")
        print("\nAllowed locations: tests, stories, fixtures, explicit demo paths, or governance/frontend_mock_exceptions.yml")
        return 1

    print("No silent frontend mocks detected in official frontend surfaces.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
