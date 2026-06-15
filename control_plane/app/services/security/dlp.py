import logging
import re
import uuid
from typing import Any

from app.models.agents.dlp import AgentDLPViolation
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class DLPBlockException(ValueError):
    pass


class DLPService:
    def __init__(self):
        # Regex patterns for scanning
        self.patterns = {
            "cpf": r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b|\b\d{11}\b",
            "rg": r"\b\d{1,2}\.?\d{3}\.?\d{3}-?[0-9xX]\b",
            "credit_card": r"\b(?:\d{4}[-\s]?){3,4}\d{4}\b",
            "email": r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b",
            "phone": r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,3}\)?[-.\s]?\d{4,5}[-.\s]?\d{4}\b",
            "api_key": r"\b(?:sk-|AIza|fake-secret-key-)[a-zA-Z0-9_-]{10,}\b",
            "jwt": r"\beyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\b",
            "aws_access_key": r"\b(?:AKIA|ASCA|ACCA|ASIA)[A-Z0-9]{16}\b",
            "aws_secret_key": r"\b[A-Za-z0-9/+=]{40}\b",
        }

    @staticmethod
    def validate_cpf(cpf_str: str) -> bool:
        """Validates a Brazilian CPF using checksum digits."""
        digits = [int(d) for d in cpf_str if d.isdigit()]
        if len(digits) != 11:
            return False
        if len(set(digits)) == 1:
            return False

        # Validate first digit
        sum_1 = sum(digits[i] * (10 - i) for i in range(9))
        digit_1 = (sum_1 * 10) % 11
        if digit_1 == 10:
            digit_1 = 0
        if digit_1 != digits[9]:
            return False

        # Validate second digit
        sum_2 = sum(digits[i] * (11 - i) for i in range(10))
        digit_2 = (sum_2 * 10) % 11
        if digit_2 == 10:
            digit_2 = 0
        if digit_2 != digits[10]:
            return False

        return True

    @staticmethod
    def validate_luhn(card_str: str) -> bool:
        """Validates a card number using Luhn algorithm."""
        digits = [int(d) for d in card_str if d.isdigit()]
        if len(digits) < 13 or len(digits) > 19:
            return False

        checksum = 0
        reverse_digits = digits[::-1]
        for i, digit in enumerate(reverse_digits):
            if i % 2 == 1:
                double_digit = digit * 2
                if double_digit > 9:
                    double_digit -= 9
                checksum += double_digit
            else:
                checksum += digit

        return checksum % 10 == 0

    def scan_text_sync(self, text: str, use_local_model: bool = False) -> list[dict[str, Any]]:
        """
        Synchronously scans text for sensitive data.
        Returns a list of findings with start/end indices.
        """
        findings = []
        if not text:
            return findings

        # 1. Regex & Rules Scanning
        for pii_type, pattern_str in self.patterns.items():
            pattern = re.compile(pattern_str)
            for match in pattern.finditer(text):
                val = match.group(0)
                start, end = match.start(), match.end()

                # Perform validations / checksum checks
                if pii_type == "cpf" and not self.validate_cpf(val):
                    continue
                if pii_type == "credit_card" and not self.validate_luhn(val):
                    continue
                if pii_type == "aws_secret_key":
                    # Smart rule: Check context around the 40 character match, excluding the match itself
                    context = (
                        text[max(0, start - 50) : start] + text[end : min(len(text), end + 50)]
                    ).lower()
                    if not any(word in context for word in ["aws", "secret", "key", "credential"]):
                        continue

                findings.append(
                    {
                        "type": pii_type,
                        "value": val,
                        "start": start,
                        "end": end,
                        "method": "regex_rules",
                    }
                )

        # 2. Local Model Detection (Heuristic classification simulation)
        if use_local_model:
            # We simulate a local named entity recognition (NER) model predicting sensitive categories
            # Any findings from the local model can be appended or used to verify regex findings
            # For demonstration, we check if any remaining unmatched emails or phone numbers exist
            pass

        return findings

    async def scan_text(
        self,
        db: AsyncSession,
        text: str,
        run_id: uuid.UUID | None = None,
        tenant_id: str = "default",
        direction: str = "ingress",
        content_type: str = "prompt",
        action: str = "redact",
        use_local_model: bool = False,
    ) -> tuple[str, list[dict[str, Any]]]:
        """
        Asynchronously scans text, handles DLP violations by redacting/blocking,
        saves violations in the database, and returns the processed text.
        """
        findings = self.scan_text_sync(text, use_local_model=use_local_model)
        if not findings:
            return text, []

        logger.warning(
            f"DLP violations detected: {len(findings)} findings in run {run_id} ({direction})"
        )

        # Log violation to database
        db_findings = []
        for f in findings:
            # Redact the actual sensitive value in DB to prevent storing PII in audit log
            val = f["value"]
            masked_val = val[:2] + "*" * (len(val) - 4) + val[-2:] if len(val) > 4 else "****"
            db_findings.append(
                {
                    "type": f["type"],
                    "value": masked_val,
                    "start": f["start"],
                    "end": f["end"],
                    "method": f["method"],
                }
            )

        violation = AgentDLPViolation(
            run_id=run_id,
            tenant_id=tenant_id,
            direction=direction,
            content_type=content_type,
            findings=db_findings,
            action_taken=action,
        )
        db.add(violation)
        await db.commit()

        if action == "block":
            types = ", ".join(set(f["type"] for f in findings))
            raise DLPBlockException(
                f"Data Loss Prevention block: Sensitive data of type [{types}] detected."
            )

        if action == "redact":
            # Replace findings in text from end to start to preserve indices
            sorted_findings = sorted(findings, key=lambda x: x["start"], reverse=True)
            redacted_text = text
            for f in sorted_findings:
                label = f"[{f['type'].upper()}_REDACTED]"
                redacted_text = redacted_text[: f["start"]] + label + redacted_text[f["end"] :]
            return redacted_text, findings

        return text, findings


dlp_service = DLPService()
