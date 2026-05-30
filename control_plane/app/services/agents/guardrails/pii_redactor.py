# Owner: agent-platform
import re
from typing import Tuple

class PIIRedactor:
    """
    Redacts Personally Identifiable Information (PII) from text.
    """
    def __init__(self):
        self.pii_patterns = {
            "email": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
            "phone": r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
            "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b"
        }

    def redact(self, text: str) -> Tuple[str, int]:
        """
        Redacts PII from the given text.
        Returns (redacted_text, count_of_redactions).
        """
        redacted_text = text
        total_redactions = 0
        
        for pii_type, pattern in self.pii_patterns.items():
            matches = re.findall(pattern, redacted_text)
            total_redactions += len(matches)
            redacted_text = re.sub(pattern, f"[{pii_type.upper()} REDACTED]", redacted_text)
            
        return redacted_text, total_redactions
