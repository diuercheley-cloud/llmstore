import re

from .graph_models import Relation


class GraphPolicy:
    def validate_tenant(
        self, requested_tenant_id: str, resource_tenant_id: str | None = None
    ) -> bool:
        if not requested_tenant_id:
            raise ValueError("tenant_id is required")
        if resource_tenant_id and requested_tenant_id != resource_tenant_id:
            raise PermissionError("Cross-tenant graph access is blocked")
        return True

    def check_provenance(self, relation: Relation) -> bool:
        if not relation.provenance:
            raise ValueError("Provenance is required")
        return True

    def require_writes_enabled(self, enabled: bool) -> None:
        if not enabled:
            raise PermissionError("Knowledge graph write path is disabled by feature flag")

    def redact_secrets(self, text: str) -> str:
        text = re.sub(r"AKIA[0-9A-Z]{12,}", "[REDACTED]", text)
        text = re.sub(
            r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][^'\"]+['\"]",
            r"\1=[REDACTED]",
            text,
        )
        return text


graph_policy = GraphPolicy()
