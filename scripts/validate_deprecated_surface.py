#!/usr/bin/env python3
"""
Validator for deprecated surfaces across the codebase.

Checks:
1. All deprecated entries (api, capability, feature_flag, python_module, shim)
   have a prazo (deadline/removal_date/sunset_date/remove_after).
2. All deprecated entries have an owner.
3. All deprecated entries have a replacement or justification.
4. Shims/compat layers past their deadline are flagged for removal.
5. Blocks new deprecated surfaces without a deadline.
6. Blocks deprecated entries missing sunset_date in api-surface.yaml.

Usage:
    python3 scripts/validate_deprecated_surface.py
"""

from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CURRENT_VERSION = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()
CURRENT_DATE = date.today()


def _parse_version(ver: str) -> tuple[int, ...]:
    ver = ver.lstrip("vV")
    parts = []
    for p in ver.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def _version_le(v1: str, v2: str) -> bool:
    return _parse_version(v1) <= _parse_version(v2)


def _version_ge(v1: str, v2: str) -> bool:
    return _parse_version(v1) >= _parse_version(v2)


def _parse_date(d: str) -> date | None:
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y"):
        try:
            return datetime.strptime(d, fmt).date()
        except (ValueError, TypeError):
            continue
    return None


def check_api_surface() -> list[str]:
    errors: list[str] = []
    path = REPO_ROOT / "config/api-surface.yaml"
    if not path.exists():
        errors.append(f"MISSING: {path}")
        return errors

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or []

    for entry in data:
        endpoint = entry.get("endpoint") or entry.get("path", "unknown")
        method = entry.get("method", "unknown")
        status = entry.get("status", "")
        ref = f"{method} {endpoint}"

        if status != "deprecated":
            continue

        # Every deprecated endpoint MUST have:
        # 1. An owner
        if not entry.get("owner"):
            errors.append(f"[SEM_OWNER] {ref} está deprecated mas não tem owner")

        # 2. A replacement or justification
        if not entry.get("replacement") and not entry.get("justification"):
            errors.append(
                f"[SEM_SUBSTITUTO] {ref} está deprecated mas não tem replacement ou justification"
            )

        # 3. A sunset_date or removal_date
        has_deadline = bool(
            entry.get("sunset_date") or entry.get("removal_date") or entry.get("removal_version")
        )
        if not has_deadline:
            errors.append(
                f"[SEM_PRAZO] {ref} está deprecated mas não tem sunset_date, "
                f"removal_date ou removal_version"
            )

        # 4. If past deadline, flag for removal
        sunset = entry.get("sunset_date") or entry.get("removal_date")
        if sunset:
            parsed = _parse_date(str(sunset))
            if parsed and parsed < CURRENT_DATE:
                errors.append(
                    f"[PRAZO_EXPIRADO] {ref} passou do prazo de remoção "
                    f"({sunset}). Deve ser removido ou ter prazo estendido."
                )

        removal_ver = entry.get("removal_version")
        if removal_ver and _version_le(str(removal_ver), CURRENT_VERSION):
            errors.append(
                f"[VERSAO_EXPIRADA] {ref} removal_version={removal_ver} "
                f"<= current={CURRENT_VERSION}. Deve ser removido."
            )

    return errors


def check_supported_surface() -> list[str]:
    errors: list[str] = []
    path = REPO_ROOT / "config/supported-surface.yaml"
    if not path.exists():
        errors.append(f"MISSING: {path}")
        return errors

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    capabilities = data.get("capabilities", []) if isinstance(data, dict) else []

    for cap in capabilities:
        if not isinstance(cap, dict):
            continue
        cap_id = cap.get("id", "UNNAMED")
        status = cap.get("status", "")

        if status != "deprecated":
            continue

        if not cap.get("owner"):
            errors.append(f"[SEM_OWNER] Capability '{cap_id}' deprecated sem owner")

        if not cap.get("replacement") and not cap.get("limitations"):
            errors.append(
                f"[SEM_SUBSTITUTO] Capability '{cap_id}' deprecated sem replacement ou limitations"
            )

        has_deadline = bool(
            cap.get("removal_date") or cap.get("removal_version") or cap.get("sunset_date")
        )
        if not has_deadline:
            errors.append(
                f"[SEM_PRAZO] Capability '{cap_id}' deprecated sem "
                f"removal_date, removal_version ou sunset_date"
            )

        removal_ver = cap.get("removal_version")
        if removal_ver and _version_le(str(removal_ver), CURRENT_VERSION):
            errors.append(
                f"[VERSAO_EXPIRADA] Capability '{cap_id}' removal_version="
                f"{removal_ver} <= current={CURRENT_VERSION}"
            )

    return errors


def check_feature_flags() -> list[str]:
    errors: list[str] = []
    path = REPO_ROOT / "config/feature-flags.yaml"
    if not path.exists():
        errors.append(f"MISSING: {path}")
        return errors

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or []

    for entry in data:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name", "UNNAMED")
        status = entry.get("status", "")

        if status != "deprecated":
            continue

        if not entry.get("owner"):
            errors.append(f"[SEM_OWNER] Feature flag '{name}' deprecated sem owner")

        if not entry.get("replacement"):
            errors.append(f"[SEM_SUBSTITUTO] Feature flag '{name}' deprecated sem replacement")

        remove_after = entry.get("remove_after")
        if not remove_after:
            errors.append(f"[SEM_PRAZO] Feature flag '{name}' deprecated sem remove_after")
        elif _version_le(str(remove_after), CURRENT_VERSION):
            errors.append(
                f"[PRAZO_EXPIRADO] Feature flag '{name}' remove_after="
                f"{remove_after} <= current={CURRENT_VERSION}. Deve ser removido."
            )

    return errors


def check_deprecated_python_modules() -> list[str]:
    errors: list[str] = []
    checks = [
        {
            "path": "scripts/llm_harness/agent_harness.py",
            "name": "agent_harness.py",
            "owner": "agent-platform",
            "deadline_version": "v3.0",
        },
        {
            "path": "control_plane/app/services/disaster_recovery/agent_backup.py",
            "name": "AgentBackupService / BackupScheduler",
            "owner": "platform-ops",
            "deadline_version": "v3.0",
        },
        {
            "path": "control_plane/app/main.py",
            "name": "GET /static/admin deprecation shim",
            "owner": "platform-ops",
            "deadline_version": "v3.0",
        },
        {
            "path": "control_plane/app/middleware.py",
            "name": "deprecation_middleware / /agents Deprecation header",
            "owner": "platform-ops",
            "deadline_version": "v3.0",
        },
    ]

    for check in checks:
        path = REPO_ROOT / check["path"]
        if not path.exists():
            errors.append(f"[MISSING] {check['name']} ({check['path']}) não encontrado")
            continue

        content = path.read_text(encoding="utf-8")
        ref = f"{check['name']} ({check['path']})"

        # Skip whole-file deprecation check for files that contain shims within active modules
        check_path = check["path"]
        is_shim_within_active = "main.py" in check_path or "middleware.py" in check_path
        if not is_shim_within_active:
            if "DEPRECATED" not in content and "deprecated" not in content.lower():
                errors.append(f"[SEM_MARCAÇÃO] {ref} não possui marcador de deprecação")

        if not check.get("owner"):
            errors.append(f"[SEM_OWNER] {ref} sem owner")

        dver = check.get("deadline_version", "")
        if not dver:
            errors.append(f"[SEM_PRAZO] {ref} não tem prazo de remoção definido")
        elif _version_le(dver, CURRENT_VERSION):
            errors.append(
                f"[PRAZO_EXPIRADO] {ref} deadline {dver} <= "
                f"current {CURRENT_VERSION}. Deve ser removido."
            )

    return errors


def check_deprecation_shims() -> list[str]:
    errors: list[str] = []
    shims = [
        {
            "path": "control_plane/app/main.py",
            "pattern": "# Deprecation shim for legacy static admin UI",
            "name": "GET /static/admin shim",
            "owner": "platform-ops",
            "removal_version": "v3.0",
        },
        {
            "path": "control_plane/app/middleware.py",
            "pattern": "deprecation_middleware",
            "name": "deprecation_middleware",
            "owner": "platform-ops",
            "removal_version": "v3.0",
        },
    ]

    for shim in shims:
        path = REPO_ROOT / shim["path"]
        if not path.exists():
            continue

        content = path.read_text(encoding="utf-8")
        ref = f"{shim['name']} ({shim['path']})"

        if shim["pattern"] not in content:
            continue

        if not shim.get("owner"):
            errors.append(f"[SEM_OWNER] Shim {ref} não tem owner")

        if not shim.get("removal_version") and not shim.get("removal_date"):
            errors.append(
                f"[SEM_PRAZO] Shim {ref} não tem removal_version ou removal_date definido"
            )

        removal_ver = shim.get("removal_version")
        if removal_ver and _version_le(str(removal_ver), CURRENT_VERSION):
            errors.append(
                f"[PRAZO_EXPIRADO] Shim {ref} removal_version="
                f"{removal_ver} <= current={CURRENT_VERSION}"
            )

    return errors


def validate() -> list[str]:
    all_errors: list[str] = []

    all_errors.extend(check_api_surface())
    all_errors.extend(check_supported_surface())
    all_errors.extend(check_feature_flags())
    all_errors.extend(check_deprecated_python_modules())
    all_errors.extend(check_deprecation_shims())

    return all_errors


def main() -> int:
    errors = validate()

    if errors:
        print(f"\nDeprecated Surface Validation FAILED ({len(errors)} violations):\n")
        for err in sorted(errors):
            print(f"  - {err}")
        print()
        return 1

    print("\nDeprecated Surface Validation PASSED.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
