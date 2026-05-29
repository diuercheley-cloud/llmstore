class DataBoundaryPolicy:
    @staticmethod
    def sanitize_payload(payload: dict) -> dict:
        """Ensure no prompts, docs or raw memory are synced"""
        sanitized = payload.copy()
        if "prompt" in sanitized:
            del sanitized["prompt"]
        if "documents" in sanitized:
            del sanitized["documents"]
        if "memory" in sanitized:
            del sanitized["memory"]
        return sanitized