from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CONTROL_PLANE_ROOT = ROOT / "control_plane"
APP_ROOT = CONTROL_PLANE_ROOT / "app"

if str(CONTROL_PLANE_ROOT) not in sys.path:
    sys.path.insert(0, str(CONTROL_PLANE_ROOT))


AUDIT_PREFIXES = (
    "app.api.audit",
    "app.domains.audit",
    "app.services.audit",
)

API_INFRASTRUCTURE_PREFIXES = (
    "app.db",
    "app.services.cache.semantic_cache_redis",
    "app.services.inference.backends",
    "app.services.routing.infra_adapters",
)

API_INFRASTRUCTURE_XFAIL = (
    "Large existing API->infra coupling tracked in issue ARCH-API-INFRA-001; deadline 2026-07-31."
)


@dataclass(frozen=True)
class ImportEdge:
    importer: str
    imported: str
    line: int


def _module_name(path: Path) -> str:
    relative = path.relative_to(CONTROL_PLANE_ROOT).with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _resolve_import_from(*, module_name: str, node: ast.ImportFrom) -> str | None:
    if node.module is None and node.level == 0:
        return None

    package_parts = module_name.split(".")
    if node.level:
        package_parts = package_parts[: -node.level]
    if node.module:
        return ".".join([*package_parts, node.module])
    return ".".join(package_parts)


def _iter_internal_imports(path: Path) -> list[ImportEdge]:
    module_name = _module_name(path)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    edges: list[ImportEdge] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("app."):
                    edges.append(ImportEdge(module_name, alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            imported = _resolve_import_from(module_name=module_name, node=node)
            if imported and imported.startswith("app."):
                edges.append(ImportEdge(module_name, imported, node.lineno))

    return edges


def _all_import_edges() -> list[ImportEdge]:
    edges: list[ImportEdge] = []
    for path in APP_ROOT.rglob("*.py"):
        edges.extend(_iter_internal_imports(path))
    return edges


def _is_audit_module(module_name: str) -> bool:
    return module_name.startswith(AUDIT_PREFIXES)


def _matches_prefix(module_name: str, prefixes: tuple[str, ...]) -> bool:
    return module_name.startswith(prefixes)


def _format_violations(violations: list[ImportEdge]) -> str:
    rendered = []
    for violation in sorted(violations, key=lambda edge: (edge.importer, edge.line, edge.imported)):
        rendered.append(
            f"{violation.importer.replace('.', '/')}.py:{violation.line} imports {violation.imported}"
        )
    return "\n".join(rendered)


@pytest.fixture(scope="module")
def import_edges() -> list[ImportEdge]:
    return _all_import_edges()


def test_services_do_not_import_api(import_edges: list[ImportEdge]) -> None:
    violations = [
        edge
        for edge in import_edges
        if edge.importer.startswith("app.services.")
        and edge.imported.startswith("app.api.")
        and not _is_audit_module(edge.imported)
    ]
    assert not violations, _format_violations(violations)


def test_models_do_not_import_services(import_edges: list[ImportEdge]) -> None:
    violations = [
        edge
        for edge in import_edges
        if edge.importer.startswith("app.models.")
        and edge.imported.startswith("app.services.")
        and not _is_audit_module(edge.imported)
    ]
    assert not violations, _format_violations(violations)


def test_api_does_not_import_infrastructure_details(import_edges: list[ImportEdge]) -> None:
    violations = [
        edge
        for edge in import_edges
        if edge.importer.startswith("app.api.")
        and _matches_prefix(edge.imported, API_INFRASTRUCTURE_PREFIXES)
        and not _is_audit_module(edge.imported)
    ]
    if violations:
        pytest.xfail(f"{API_INFRASTRUCTURE_XFAIL}\n{_format_violations(violations)}")


def test_billing_does_not_depend_on_agents_directly(import_edges: list[ImportEdge]) -> None:
    billing_prefixes = (
        "app.domains.billing",
        "app.models.billing",
        "app.services.billing",
    )
    agent_prefixes = (
        "app.contracts.agents",
        "app.models.agents",
        "app.services.agents",
    )
    violations = [
        edge
        for edge in import_edges
        if _matches_prefix(edge.importer, billing_prefixes)
        and _matches_prefix(edge.imported, agent_prefixes)
        and not _is_audit_module(edge.imported)
    ]
    assert not violations, _format_violations(violations)
