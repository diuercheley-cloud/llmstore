# Owner: agent-platform
class PhoenixExporter:
    def export(self, payload: dict) -> dict:
        return {"backend": "phoenix", "accepted": False, "payload": payload}
