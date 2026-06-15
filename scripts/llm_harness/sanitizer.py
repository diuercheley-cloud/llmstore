import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class Sanitizer:
    """
    Cleans and validates data from untrusted sources (like LLMs).
    """

    @staticmethod
    def clean_markdown(content: str) -> str:
        """
        Extract code blocks from markdown or clean surrounding text.
        """
        # Find the first python code block
        match = re.search(r"```python\n(.*?)\n```", content, re.DOTALL)
        if match:
            return match.group(1)
        return content

    @staticmethod
    def strip_control_chars(content: str) -> str:
        """
        Remove non-printable characters.
        """
        return "".join(ch for ch in content if ch.isprintable() or ch in "\n\r\t")

    @staticmethod
    def sanitize_text(content: Any) -> str:
        """
        Redact common secrets from free-form text.
        """
        if content is None:
            return ""

        text = str(content)
        patterns = [
            (
                re.compile(r"(?<![A-Z0-9])AKIA[0-9A-Z]{16}(?![A-Z0-9])"),
                "[REDACTED_AWS_KEY]",
            ),
            (
                re.compile(
                    r"-----BEGIN[A-Z\s]*PRIVATE KEY-----[ \s\S]*?"
                    r"-----END[A-Z\s]*PRIVATE KEY-----"
                ),
                "[REDACTED_PEM_KEY]",
            ),
            (
                re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
                "[REDACTED_JWT]",
            ),
            (
                re.compile(r"(?i)authorization\s*:\s*bearer\s+[^\s,;]+"),
                "Authorization: Bearer [REDACTED]",
            ),
            (
                re.compile(r"(?i)\bbearer\s+[a-z0-9._\-~=+/]+\b"),
                "Bearer [REDACTED]",
            ),
            (
                re.compile(
                    r"(?i)(\b(?:api_key|token|access_token|auth|authorization|sig|signature|password|secret)\s*[:=]\s*)([^\s,;&?]+)"
                ),
                r"\1[REDACTED]",
            ),
            (
                re.compile(r"(?i)(https?://)([^/@:\s]+):([^/@\s]+)@"),
                r"\1[REDACTED]:[REDACTED]@",
            ),
            (
                re.compile(
                    r"(?i)([?&](?:api_key|token|access_token|auth|authorization|sig|signature|password|secret)=)([^&#\s]+)"
                ),
                r"\1[REDACTED]",
            ),
        ]

        for pattern, replacement in patterns:
            text = pattern.sub(replacement, text)
        return text

    @classmethod
    def sanitize_data(cls, value: Any) -> Any:
        """
        Recursively sanitize common container types.
        """
        if isinstance(value, str) and (value.startswith("data:image/") or ";base64," in value):
            return "[REDACTED_IMAGE_BASE64]"
        if isinstance(value, dict):
            return {str(k): cls.sanitize_data(v) for k, v in value.items()}
        if isinstance(value, list):
            return [cls.sanitize_data(item) for item in value]
        if isinstance(value, tuple):
            return [cls.sanitize_data(item) for item in value]
        if isinstance(value, str):
            return cls.sanitize_text(value)
        return value
