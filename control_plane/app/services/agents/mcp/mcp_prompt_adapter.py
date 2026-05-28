# Owner: agent-platform
from typing import Any


class MCPPromptAdapter:
    def adapt(self, prompt: dict[str, Any]) -> dict[str, Any]:
        return {
            "name": prompt.get("name"),
            "description": prompt.get("description", ""),
            "arguments": prompt.get("arguments", []),
        }
