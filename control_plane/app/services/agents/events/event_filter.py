# Owner: agent-platform
import logging
from typing import Dict, Any

class EventFilter:
    """
    Filters events based on JSONPath or simple expressions.
    """
    def matches(self, payload: Dict[str, Any], expression: str) -> bool:
        """
        Evaluates the filter expression against the payload.
        Example expression: "$.type == 'order_created'"
        """
        if not expression:
            return True

        # Simplistic implementation for now: exact match check for top-level keys
        # In real life: use jsonpath-ng or similar.
        try:
            # key=value
            if "==" in expression:
                key, value = expression.split("==")
                key = key.strip().replace("$.", "")
                value = value.strip().strip("'").strip('"')
                return str(payload.get(key)) == value
            return True
        except Exception:
            return False
