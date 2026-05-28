# Owner: agent-platform
import re


class MemorySummarizer:
    def summarize(self, texts: list[str]) -> str:
        sanitized = []
        for text in texts:
            redacted = re.sub(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*[^,\n]+", r"\1=[REDACTED]", text)
            sanitized.append(redacted)
        combined = "\n".join(sanitized)
        return combined[:2000]
