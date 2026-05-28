# Owner: agent-platform
from typing import Any


class MCPResourceAdapter:
    def adapt(self, resource: dict[str, Any]) -> dict[str, Any]:
        return {
            "uri": resource.get("uri"),
            "name": resource.get("name"),
            "mime_type": resource.get("mime_type", "text/plain"),
        }
