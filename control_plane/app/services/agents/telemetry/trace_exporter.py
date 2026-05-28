# Owner: agent-platform
class TraceExporter:
    def export(self, payload: dict) -> dict:
        return {"exported": False, "reason": "external export disabled by default", "payload": payload}
