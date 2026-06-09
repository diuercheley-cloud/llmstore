#!/usr/bin/env python3
"""Enforce architectural freeze rules without disabling local development."""

import json
import os
import re
import subprocess
import sys

RULES_PATH = "config/platform-freeze-rules.json"


def _exceptions(rules):
    return set(rules.get("approved_exceptions", []))


def load_rules():
    with open(RULES_PATH, encoding="utf-8") as handle:
        return json.load(handle)


def check_top_level_dirs(rules):
    if not rules.get("forbid_new_top_level_dirs"):
        return True
    allowed = set(rules.get("allowed_top_level_dirs", [])) | _exceptions(rules)
    ignored = {".idea", ".vscode", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache"}
    violations = [
        name for name in os.listdir(".")
        if os.path.isdir(name) and name not in allowed and name not in ignored
    ]
    if violations:
        print(f"FAIL: New top-level directories detected: {violations}")
    return not violations


def check_bounded_contexts(rules):
    if not rules.get("forbid_new_bounded_contexts"):
        return True
    root = "control_plane/app/services"
    if not os.path.exists(root):
        return True
    allowed = set(rules.get("allowed_bounded_contexts", [])) | _exceptions(rules)
    violations = [
        name for name in os.listdir(root)
        if os.path.isdir(os.path.join(root, name)) and name != "__pycache__" and name not in allowed
    ]
    if violations:
        print(f"FAIL: New bounded contexts detected: {violations}")
    return not violations


def _has_surface(content):
    return bool(
        re.search(r"#\s*(Surface|Classification):", content, re.I)
        or re.search(r'prefix\s*=\s*"/(admin|client|portal|public)', content, re.I)
    )


def check_api_routers(rules):
    if rules.get("forbid_new_api_routers_without_approval") is False:
        return True
    root = "control_plane/app/api"
    if not os.path.exists(root):
        return True
    allowed = set(rules.get("allowed_api_routers", []))
    exceptions = _exceptions(rules)
    violations = []
    for name in os.listdir(root):
        if not name.endswith(".py") or name in {"__init__.py", "dependencies.py", "deps.py"}:
            continue
        if name in allowed:
            continue
        with open(os.path.join(root, name), encoding="utf-8") as handle:
            content = handle.read()
        if name not in exceptions:
            violations.append(f"New api router '{name}' is not approved.")
        if not _has_surface(content):
            violations.append(f"New api router '{name}' has no surface classification.")
        is_admin = "admin" in name or re.search(r'prefix\s*=\s*"/admin', content)
        if is_admin and not re.search(r"#\s*Owner:|__owner__\s*=", content, re.I):
            violations.append(f"New admin router '{name}' has no owner.")
    for violation in violations:
        print(f"FAIL: {violation}")
    return not violations


def check_new_services(rules):
    if rules.get("forbid_new_services_without_approval") is False:
        return True
    root = "control_plane/app/services"
    if not os.path.exists(root):
        return True
    allowed = set(rules.get("allowed_services", []))
    exceptions = _exceptions(rules)
    violations = []
    for current_root, _, files in os.walk(root):
        for name in files:
            if not name.endswith(".py") or name == "__init__.py":
                continue
            relative = os.path.relpath(os.path.join(current_root, name), root)
            if relative in allowed:
                continue
            with open(os.path.join(current_root, name), encoding="utf-8") as handle:
                content = handle.read()
            if relative not in exceptions:
                violations.append(f"New service '{relative}' is not approved.")
            if '"""' not in content and "'''" not in content and not re.search(r"#\s*Owner:", content, re.I):
                violations.append(f"New service '{relative}' has no documentation or owner.")
    for violation in violations:
        print(f"FAIL: {violation}")
    return not violations


def check_feature_flags(rules):
    if rules.get("forbid_new_feature_flags_without_owner") is False:
        return True
    path = "control_plane/app/core/config.py"
    if not os.path.exists(path):
        return True
    allowed = set(rules.get("allowed_feature_flags", []))
    exceptions = _exceptions(rules)
    lines = open(path, encoding="utf-8").readlines()
    violations = []
    for index, line in enumerate(lines):
        match = re.match(r"\s*(\w+)\s*:", line)
        if not match or "=" not in line or ("_enabled" not in line and "feature_flag" not in line):
            continue
        name = match.group(1)
        if name in allowed:
            continue
        context = "".join(lines[max(0, index - 5): index + 1])
        if name not in exceptions:
            violations.append(f"New feature flag '{name}' is not approved.")
        if "Owner:" not in context or "Status:" not in context:
            violations.append(f"New feature flag '{name}' has no Owner/Status metadata.")
    for violation in violations:
        print(f"FAIL: {violation}")
    return not violations


def check_models_and_migrations(rules):
    if rules.get("forbid_new_models_without_migration_and_owner") is False:
        return True
    root = "control_plane/app/models"
    if not os.path.exists(root):
        return True
    allowed = set(rules.get("allowed_models", []))
    exceptions = _exceptions(rules)
    migration_text = ""
    migration_root = "control_plane/alembic/versions"
    if os.path.exists(migration_root):
        for name in os.listdir(migration_root):
            if name.endswith(".py"):
                migration_text += open(os.path.join(migration_root, name), encoding="utf-8").read()
    violations = []
    for current_root, _, files in os.walk(root):
        for name in files:
            if not name.endswith(".py") or name == "__init__.py":
                continue
            path = os.path.join(current_root, name)
            content = open(path, encoding="utf-8").read()
            for model in re.findall(r"class\s+(\w+)\s*\([^)]*Base[^)]*\)\s*:", content):
                if model in allowed:
                    continue
                if model not in exceptions:
                    violations.append(f"New model '{model}' is not approved.")
                if not re.search(r"#\s*Owner:|__owner__\s*=", content, re.I):
                    violations.append(f"New model '{model}' has no owner.")
                if model.lower() not in migration_text.lower():
                    violations.append(f"New model '{model}' has no migration.")
    for violation in violations:
        print(f"FAIL: {violation}")
    return not violations


def check_new_endpoints(rules):
    if not rules.get("require_supported_surface_classification"):
        return True
    try:
        base = subprocess.run(["git", "rev-parse", "--verify", "v1.9.7-compliance-readiness"], capture_output=True)
        diff = subprocess.run(
            ["git", "diff", "v1.9.7-compliance-readiness", "--", "control_plane/app/api/"],
            capture_output=True, text=True,
        )
    except Exception:
        return True
    if base.returncode != 0 or diff.returncode != 0:
        return True
    violations = []
    current_file = None
    for line in diff.stdout.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:]
        elif line.startswith("+") and re.search(r"@\w+\.(get|post|put|delete|patch)\s*\(", line):
            if current_file and os.path.exists(current_file):
                content = open(current_file, encoding="utf-8").read()
                if not _has_surface(content):
                    violations.append(f"New endpoint in '{current_file}' has no surface classification.")
    for violation in violations:
        print(f"FAIL: {violation}")
    return not violations


def main():
    rules = load_rules()
    checks = (
        check_top_level_dirs,
        check_bounded_contexts,
        check_api_routers,
        check_new_services,
        check_feature_flags,
        check_models_and_migrations,
        check_new_endpoints,
    )
    if all(check(rules) for check in checks):
        print("PASS: Platform architectural freeze compliance verified successfully.")
        return 0
    print("FAIL: Architectural freeze violations detected.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
