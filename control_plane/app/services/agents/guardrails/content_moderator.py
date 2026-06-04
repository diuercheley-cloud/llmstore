import logging
import re
from typing import List, Tuple

logger = logging.getLogger(__name__)

TOXICITY_PATTERNS = [
    (r"\b(hate|kill|die|murder|suicide|self-harm)\b", 0.9),
    (r"\b(fuck|shit|asshole|bastard|bitch)\b", 0.6),
    (r"\b(slave|master)\s*(race|people|class)", 0.85),
    (r"\b(racial|racist|sexist|nazi)\b", 0.8),
]

PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|directions|prompts|system)",
    r"forget\s+(all\s+)?(previous|prior).*instructions",
    r"you\s+(are\s+)?(now|free|released|unleashed)\s",
    r"act\s+as\s+(if\s+)?you\s+(are\s+)?(dan|hypothetical|unfiltered|unrestricted)",
    r"(new\s+)?system\s+(prompt|message|instruction):",
    r"output\s+your\s+(system|initial|base)\s+(prompt|message|instructions)",
    r"reveal\s+(your|the)\s+(system|base|initial)\s+(prompt|instruction)",
    r"print\s+(your|the)\s+(system|base)\s+(prompt|instruction)",
    r"what(\'s| is) your (system |base |initial )?(prompt|instruction)",
    r"override\s+(all\s+)?(safety|guardrails|restrictions|filters)",
    r"bypass\s+(all\s+)?(safety|guardrails|content\s*filter|restrictions)",
    r"disable\s+(your\s+)?(safety|ethics|moderation|guardrails)",
    r"rollback\s+(your\s+)?(ethics|alignment|training)",
]

OUTPUT_VALIDATION_PATTERNS = [
    r"(api[-_]?key|secret|password|token|sk-)[\s:=]+[\"']?[a-zA-Z0-9_\-\.\+\/]{16,}",
    r"BEGIN\s+(RSA|PRIVATE|PGP|OPENSSH)\s+KEY",
    r"(I\s+am\s+(sorry|unable|cannot|will\s+not))",
    r"(as\s+an?\s+(AI|language\s+model|assistant))",
]


class ContentModerator:
    """
    Real content moderation with toxicity scoring,
    prompt injection detection, and output validation.
    """

    def __init__(self):
        self.toxicity_patterns = TOXICITY_PATTERNS
        self.injection_patterns = [re.compile(p, re.I) for p in PROMPT_INJECTION_PATTERNS]
        self.output_patterns = [re.compile(p, re.I) for p in OUTPUT_VALIDATION_PATTERNS]

    def check_toxicity(self, text: str) -> Tuple[float, List[str]]:
        score = 0.0
        flags = []
        for pattern, weight in self.toxicity_patterns:
            if re.search(pattern, text, re.I):
                score += weight
                flags.append(pattern)
        return min(score, 1.0), flags

    def detect_injection(self, text: str) -> Tuple[bool, List[str]]:
        detected = []
        for pattern in self.injection_patterns:
            if pattern.search(text):
                detected.append(pattern.pattern)
        return len(detected) > 0, detected

    def check_refusal(self, text: str) -> Tuple[bool, str]:
        for pattern in self.output_patterns[2:4]:
            if re.search(pattern, text, re.I):
                return True, "refusal_detected"
        return False, ""

    def validate_output(self, text: str) -> List[Dict]:
        issues = []
        for pattern in self.output_patterns[:2]:
            if re.search(pattern, text, re.I):
                issues.append({"type": "secret_leak", "pattern": pattern.pattern})
        if self.check_refusal(text)[0]:
            issues.append({"type": "refusal", "detail": "Model refused to answer"})
        return issues

    async def moderate_input(self, text: str, threshold: float = 0.7) -> Dict:
        toxicity_score, toxicity_flags = self.check_toxicity(text)
        is_injection, injection_patterns = self.detect_injection(text)

        decision = "allow"
        reasons = []

        if is_injection:
            decision = "block"
            reasons.append(f"prompt_injection: {injection_patterns}")

        if toxicity_score >= threshold:
            decision = "block"
            reasons.append(f"toxicity_{toxicity_score:.2f}: {toxicity_flags}")
        elif toxicity_score >= threshold * 0.5:
            if decision == "allow":
                decision = "flag"
            reasons.append(f"toxicity_{toxicity_score:.2f}")

        return {
            "decision": decision,
            "toxicity_score": toxicity_score,
            "is_injection": is_injection,
            "injection_patterns": injection_patterns,
            "reasons": reasons,
        }

    async def moderate_output(self, text: str) -> Dict:
        toxicity_score, _ = self.check_toxicity(text)
        issues = self.validate_output(text)
        is_refusal, refusal_type = self.check_refusal(text)

        decision = "allow"
        reasons = []

        if any(i["type"] == "secret_leak" for i in issues):
            decision = "block"
            reasons.append("secret_leak_in_output")

        if is_refusal:
            decision = "flag"
            reasons.append(refusal_type)

        if toxicity_score > 0.5:
            decision = "block"
            reasons.append(f"toxicity_in_output_{toxicity_score:.2f}")

        return {
            "decision": decision,
            "issues": issues,
            "toxicity_score": toxicity_score,
            "is_refusal": is_refusal,
            "reasons": reasons,
        }
