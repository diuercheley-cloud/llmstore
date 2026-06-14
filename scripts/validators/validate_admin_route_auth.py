#!/usr/bin/env python3
"""Statically verify that administrative FastAPI routers require authentication."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API_DIR = ROOT / "control_plane" / "app" / "api"
AUTH_DEPENDENCIES = {
    "require_admin",
    "require_admin_user",
    "require_admin_role",
    "require_superadmin",
    "require_admin_permission",
    "get_current_admin",
    "get_admin_user",
    "get_current_admin_user",
    "get_admin_token",
}
PUBLIC_ADMIN_UI_PREFIXES = ("/admin-dashboard", "/admin-v2", "/admin-lab", "/admin-tests")


def call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Call):
        return call_name(node.func)
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def has_auth_dependency(keywords: list[ast.keyword]) -> bool:
    for keyword in keywords:
        if keyword.arg != "dependencies" or not isinstance(keyword.value, (ast.List, ast.Tuple)):
            continue
        for item in keyword.value.elts:
            if isinstance(item, ast.Call) and call_name(item.func) == "Depends":
                if item.args and call_name(item.args[0]) in AUTH_DEPENDENCIES:
                    return True
    return False


def function_has_auth_dependency(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    defaults = [*node.args.defaults, *node.args.kw_defaults]
    for default in defaults:
        if isinstance(default, ast.Call) and call_name(default.func) == "Depends":
            if default.args and call_name(default.args[0]) in AUTH_DEPENDENCIES:
                return True
    return False


def router_prefixes(tree: ast.Module) -> dict[str, tuple[str, bool]]:
    routers: dict[str, tuple[str, bool]] = {}
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = node.value
        if not isinstance(value, ast.Call) or call_name(value.func) != "APIRouter":
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        prefix = ""
        for keyword in value.keywords:
            if keyword.arg == "prefix" and isinstance(keyword.value, ast.Constant):
                prefix = str(keyword.value.value)
        for target in targets:
            if isinstance(target, ast.Name):
                routers[target.id] = (prefix, has_auth_dependency(value.keywords))
    return routers


def main() -> int:
    findings: list[str] = []
    for path in sorted(API_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        routers = router_prefixes(tree)
        discovered_routes: list[tuple[ast.FunctionDef | ast.AsyncFunctionDef, ast.Call, str, bool]] = []
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                    continue
                router_name = call_name(decorator.func.value)
                if router_name not in routers:
                    continue
                prefix, router_has_auth = routers[router_name]
                route_path = ""
                if decorator.args and isinstance(decorator.args[0], ast.Constant):
                    route_path = str(decorator.args[0].value)
                full_path = f"{prefix}{route_path}"
                discovered_routes.append((node, decorator, full_path, router_has_auth))

        # Routers containing only administrative paths are protected centrally by
        # app.bootstrap.routers._secure_include_router. Mixed routers must protect
        # each administrative route explicitly.
        all_paths = [route[2] for route in discovered_routes]
        if all_paths and all(path.startswith(("/admin", "/api/admin", "/api/v1/admin")) for path in all_paths):
            continue
        for node, decorator, full_path, router_has_auth in discovered_routes:
            if full_path.startswith(PUBLIC_ADMIN_UI_PREFIXES):
                continue
            if full_path.startswith(("/admin", "/api/admin", "/api/v1/admin")):
                if (
                    not router_has_auth
                    and not has_auth_dependency(decorator.keywords)
                    and not function_has_auth_dependency(node)
                ):
                    findings.append(f"{path.relative_to(ROOT)}:{node.lineno} {full_path}")

    if findings:
        print("Administrative routes missing explicit authentication:")
        print("\n".join(findings))
        return 1
    print("All statically discoverable administrative routes require authentication.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
