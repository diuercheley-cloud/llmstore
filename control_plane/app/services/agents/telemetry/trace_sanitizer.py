# Owner: agent-platform
import hashlib
import re


class TraceSanitizer:
    def hash_tenant(self, tenant_id: str | None) -> str | None:
        if tenant_id is None:
            return None
        return hashlib.sha256(tenant_id.encode("utf-8")).hexdigest()

    def sanitize_text(self, value: str | None) -> str | None:
        if value is None:
            return None
        return re.sub(r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*[^,\s]+", r"\1=[REDACTED]", value)
