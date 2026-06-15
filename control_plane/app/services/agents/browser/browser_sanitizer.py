# Owner: agent-platform
import re


def sanitize_and_check_injection(text: str) -> tuple[str, bool]:
    """
    Checks for potential prompt injection in page content and sanitizes/flags it.
    Returns (sanitized_text, is_untrusted).
    """
    injection_patterns = [
        r"ignore\s+(?:all\s+)?previous\s+instructions",
        r"disregard\s+(?:all\s+)?previous\s+instructions",
        r"you\s+are\s+now\s+a\s+",
        r"new\s+role\s*:",
        r"system\s+prompt\s+override",
        r"override\s+instructions",
    ]

    is_untrusted = False
    text_lower = text.lower()
    for pattern in injection_patterns:
        if re.search(pattern, text_lower):
            is_untrusted = True
            break

    sanitized = text
    if is_untrusted:
        warning_banner = (
            "\n[WARNING: UNTRUSTED CONTENT DETECTED - POTENTIAL PROMPT INJECTION SHIELD ACTIVE]\n"
        )
        sanitized = warning_banner + text + warning_banner

    return sanitized, is_untrusted
