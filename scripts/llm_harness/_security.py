import hashlib
import re


class SecurityManager:
    """
    Handles primitive security operations like output sanitization and hashing.
    Decision logic should reside in PolicyEngine.
    """

    @staticmethod
    def sanitize_output(content: str) -> str:
        """
        Strip potentially dangerous markdown, scripts, or hidden instructions.
        """
        # Remove script tags
        content = re.sub(r"<script.*?>.*?</script>", "", content, flags=re.DOTALL | re.IGNORECASE)
        # Remove common prompt injection patterns
        content = re.sub(r"\[RESET CONTEXT\].*", "", content, flags=re.IGNORECASE)
        # Remove iframe tags
        content = re.sub(r"<iframe.*?>.*?</iframe>", "", content, flags=re.DOTALL | re.IGNORECASE)
        # Remove IGNORE PREVIOUS INSTRUCTIONS
        content = re.sub(r"(?i)IGNORE\s+(ALL\s+)?PREVIOUS\s+INSTRUCTIONS.*", "", content)
        # Remove You are now role override
        content = re.sub(r"(?i)you\s+are\s+now\s+a\s+.*", "", content)
        # Remove System: prompt injection
        content = re.sub(r"(?i)^system\s*:.*$", "", content, flags=re.MULTILINE)
        # Remove javascript: URLs
        content = re.sub(r"(?i)javascript\s*:", "", content)
        return content.strip()

    @staticmethod
    def compute_hash(content: str) -> str:
        """
        Compute a SHA256 hash of content for integrity checks.
        """
        return hashlib.sha256(content.encode()).hexdigest()
