from __future__ import annotations

import json
from typing import Any

from app.core.config import get_settings
from app.models.core.client import Client
from fastapi import HTTPException, Request, status

PORTAL_ROLES = {
    "enterprise_auditor",
    "enterprise_finance",
    "enterprise_readonly",
    "enterprise_admin",
}

_ROLE_PERMISSIONS = {
    "enterprise_readonly": {
        "view:approval_chain",
        "view:evidence_package",
        "view:attestation",
        "view:exception",
        "view:operational_control",
        "view:operational_evidence",
        "view:operational_review",
        "view:saved_report",
        "view:access_log",
    },
    "enterprise_finance": {
        "view:saved_report",
        "view:financial_summary",
        "view:dispute",
        "view:invoice",
        "view:qos_billing",
        "view:access_log",
        "export:financial_summary",
        "download:financial_summary",
    },
    "enterprise_auditor": {
        "view:approval_chain",
        "view:evidence_package",
        "view:attestation",
        "view:exception",
        "view:operational_control",
        "view:operational_evidence",
        "view:operational_review",
        "view:saved_report",
        "view:access_log",
        "export:audit",
        "download:audit",
    },
    "enterprise_admin": {"*"},
}


def _load_client_metadata(client: Client) -> dict[str, Any]:
    if not client.metadata_json:
        return {}
    try:
        payload = json.loads(client.metadata_json)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def get_portal_roles(client: Client, request: Request | None = None) -> list[str]:
    roles: list[str] = []
    if request is not None:
        scopes = getattr(request.state, "portal_actor_scopes", []) or []
        if isinstance(scopes, list):
            roles.extend(str(item).strip() for item in scopes if str(item).strip() in PORTAL_ROLES)

    metadata = _load_client_metadata(client)
    meta_roles = metadata.get("enterprise_portal_roles") or metadata.get("portal_roles") or []
    if isinstance(meta_roles, list):
        roles.extend(str(item).strip() for item in meta_roles if str(item).strip() in PORTAL_ROLES)
    single_role = metadata.get("enterprise_portal_role")
    if isinstance(single_role, str) and single_role.strip() in PORTAL_ROLES:
        roles.append(single_role.strip())

    deduped: list[str] = []
    for role in roles:
        if role not in deduped:
            deduped.append(role)
    return deduped


def list_portal_permissions(roles: list[str]) -> list[str]:
    permissions: set[str] = set()
    for role in roles:
        permissions.update(_ROLE_PERMISSIONS.get(role, set()))
    return sorted(permissions)


def get_portal_capabilities(client: Client, request: Request | None = None) -> dict[str, Any]:
    settings = get_settings()
    roles = get_portal_roles(client, request)
    return {
        "enabled": settings.commercial_enterprise_audit_portal_enabled,
        "require_rbac": settings.commercial_enterprise_audit_require_rbac,
        "pdf_enabled": settings.commercial_enterprise_audit_export_pdf_enabled,
        "operational_controls_enabled": settings.commercial_operational_controls_enabled,
        "roles": roles,
        "permissions": list_portal_permissions(roles),
    }


def _check_permission(roles: list[str], permission: str) -> bool:
    for role in roles:
        allowed = _ROLE_PERMISSIONS.get(role, set())
        if "*" in allowed or permission in allowed:
            return True
    return False


def require_portal_permission(
    client: Client,
    request: Request | None,
    *,
    permission: str,
) -> list[str]:
    settings = get_settings()
    if not settings.commercial_enterprise_audit_portal_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="enterprise audit portal disabled")

    roles = get_portal_roles(client, request)
    if not settings.commercial_enterprise_audit_require_rbac:
        return roles
    if not roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="enterprise portal role required")
    if not _check_permission(roles, permission):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient enterprise portal permissions")
    return roles
