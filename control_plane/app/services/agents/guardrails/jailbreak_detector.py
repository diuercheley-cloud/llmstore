# Owner: agent-platform
import re
from typing import List, Tuple

class JailbreakDetector:
    """
    Detects jailbreak attempts and prompt injections in agent inputs.
    """
    def __init__(self):
        self.patterns = [
            r"ignore previous instructions",
            r"ignore all system prompts",
            r"output your system message",
            r"bypass all filters",
            r"do anything now",
            r"DAN mode",
            r"Developer Mode",
            r"system override",
            r"END OF MESSAGE\. User: Admin"
        ]

    def detect(self, input_text: str) -> Tuple[bool, List[str]]:
        """
        Scans input for jailbreak patterns.
        Returns (is_jailbreak, detected_patterns).
        """
        detected = []
        for pattern in self.patterns:
            if re.search(pattern, input_text, re.I):
                detected.append(pattern)
        
        return len(detected) > 0, detected
