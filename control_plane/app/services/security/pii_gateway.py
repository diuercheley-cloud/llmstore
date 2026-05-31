import re
import logging
from typing import Any, Dict, List, Union

logger = logging.getLogger(__name__)

class PIIGateway:
    """
    Centralized PII Anonymization Gateway.
    Protects sensitive data by intercepting prompts and responses.
    """
    def __init__(self):
        # Patterns for common PII (simplified for demo, expandable)
        self.patterns = {
            "email": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
            "cpf": r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b",
            "credit_card": r"\b(?:\d{4}[ -]?){3}\d{4}\b",
            "api_key": r"(?:sk-|AIza)[a-zA-Z0-9_-]{20,}"
        }

    def redact_text(self, text: str) -> str:
        if not text:
            return text
        
        redacted = text
        for pii_type, pattern in self.patterns.items():
            redacted = re.sub(pattern, f"[{pii_type.upper()}_REDACTED]", redacted)
        
        return redacted

    def redact_payload(self, data: Union[Dict, List, Any]) -> Any:
        if isinstance(data, dict):
            return {k: self.redact_payload(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.redact_payload(item) for item in data]
        elif isinstance(data, str):
            return self.redact_text(data)
        return data

pii_gateway = PIIGateway()
