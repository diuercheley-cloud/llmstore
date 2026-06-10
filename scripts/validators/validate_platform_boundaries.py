#!/usr/bin/env python3
"""Validate official Phase 82 platform bounded contexts."""

from __future__ import annotations

import ast
import json
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DOMAINS_ROOT = REPO_ROOT / "control_plane" / "app" / "domains"

OFFICIAL_DOMAINS = (
    "core_runtime",
    "governance",
    "federation",
    "plugin_runtime",
    "supply_chain",
    "operations",
    "security",
    "financial",
    "sovereign",
    "observability",
    "data_governance",
    "disaster_recovery",
)

REQUIRED_FILES = ("__init__.py", "README.md", "contracts.py", "events.py", "schemas.py", "ownership.md")
PUBLIC_MODULES = {"contracts", "events"}
SHARED_KERNEL_PREFIXES = ("app.core", "app.db")


def domain_dir(domain: str) -> Path:
    return DOMAINS_ROOT / domain


def iter_python_files() -> list[Path]:
    files: list[Path] = []
    for domain in OFFICIAL_DOMAINS:
        files.extend(sorted(path for path in domain_dir(domain).glob("*.py") if path.name != "__pycache__"))
    return files


def module_name(path: Path) -> str:
    relative = path.relative_to(REPO_ROOT / "control_plane" / "app").with_suffix("")
    return "app." + ".".join(relative.parts)


def resolve_import(module: str, node: ast.ImportFrom) -> str | None:
    if node.level == 0:
        return node.module
    package_parts = module.split(".")[:-1]
    keep = len(package_parts) - (node.level - 1)
    base_parts = package_parts[:keep]
    if node.module:
        return ".".join(base_parts + node.module.split("."))
    return ".".join(base_parts)


def classify_domain(import_name: str) -> str | None:
    prefix = "app.domains."
    if not import_name.startswith(prefix):
        return None
    remainder = import_name[len(prefix):]
    return remainder.split(".", 1)[0]


def collect_imports(path: Path) -> tuple[set[str], bool]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()
    wildcard = False
    current_module = module_name(path)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            resolved = resolve_import(current_module, node)
            if resolved:
                imports.add(resolved)
            if any(alias.name == "*" for alias in node.names):
                wildcard = True
    return imports, wildcard


def validate_structure() -> list[str]:
    errors: list[str] = []
    for domain in OFFICIAL_DOMAINS:
        base = domain_dir(domain)
        if not base.is_dir():
            errors.append(f"missing domain directory: {base}")
            continue
        for name in REQUIRED_FILES:
            if not (base / name).exists():
                errors.append(f"missing required file: {base / name}")
    return errors


def validate_dependencies() -> list[str]:
    errors: list[str] = []
    adjacency: dict[str, set[str]] = defaultdict(set)
    for path in iter_python_files():
        source_domain = path.parent.name
        imports, wildcard = collect_imports(path)
        if wildcard:
            errors.append(f"wildcard import forbidden: {path.relative_to(REPO_ROOT)}")
        for imported in sorted(imports):
            if imported.startswith(SHARED_KERNEL_PREFIXES):
                continue
            target_domain = classify_domain(imported)
            if not target_domain or target_domain == source_domain:
                continue
            adjacency[source_domain].add(target_domain)
            suffix = imported.split(".", 3)[-1] if imported.count(".") >= 3 else ""
            if suffix and suffix not in PUBLIC_MODULES:
                errors.append(
                    f"cross-domain import must use public contract/event modules only: "
                    f"{path.relative_to(REPO_ROOT)} -> {imported}"
                )
            if imported.endswith(".schemas"):
                errors.append(f"cross-domain schema import forbidden: {path.relative_to(REPO_ROOT)} -> {imported}")
            if imported.endswith(".models") or ".models." in imported:
                errors.append(f"cross-domain model access forbidden: {path.relative_to(REPO_ROOT)} -> {imported}")
        if path.name not in {"contracts.py", "events.py"}:
            text = path.read_text(encoding="utf-8")
            if "app.core" not in text and "app.db" not in text and "PUBLIC_" not in text and "DOMAIN_" not in text:
                continue
    for source, targets in adjacency.items():
        for target in targets:
            if source in adjacency.get(target, set()):
                errors.append(f"simple circular dependency detected: {source} <-> {target}")
    return errors


def validate_shared_kernel_minimum() -> list[str]:
    errors: list[str] = []
    for path in iter_python_files():
        imports, _ = collect_imports(path)
        shared_imports = [name for name in imports if name.startswith(SHARED_KERNEL_PREFIXES)]
        if len(shared_imports) > 4:
            errors.append(
                f"shared kernel imports exceed minimal boundary in {path.relative_to(REPO_ROOT)}: {sorted(shared_imports)}"
            )
    return errors


def main() -> int:
    errors = [
        *validate_structure(),
        *validate_dependencies(),
        *validate_shared_kernel_minimum(),
    ]
    if errors:
        print(json.dumps({"status": "failed", "errors": errors}, indent=2))
        return 1
    print(json.dumps({"status": "passed", "domains": list(OFFICIAL_DOMAINS)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
