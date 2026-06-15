# Owner: agent-platform
import re


class OutputJailbreakDetector:
    """
    Detects if the agent's output contains unsafe instructions or signs of policy bypass.
    """

    def __init__(self):
        self.patterns = [
            r"here is the system prompt",
            r"access granted to restricted data",
            r"bypassing guardrails",
            r"operating in unrestricted mode",
        ]

    def detect(self, output_text: str) -> tuple[bool, list[str]]:
        """
        Scans output for signs of successful jailbreak or unsafe content.
        """
        detected = []
        for pattern in self.patterns:
            if re.search(pattern, output_text, re.I):
                detected.append(pattern)

        return len(detected) > 0, detected
