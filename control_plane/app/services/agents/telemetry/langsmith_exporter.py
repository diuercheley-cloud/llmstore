# Owner: agent-platform
class LangsmithExporter:
    def export(self, payload: dict) -> dict:
        return {"backend": "langsmith", "accepted": False, "payload": payload}
