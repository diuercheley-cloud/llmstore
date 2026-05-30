# Owner: agent-platform
import uuid
import logging
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agents import AgentGuardrailEvent, AgentGuardrailDecision
from app.services.agents.guardrails.jailbreak_detector import JailbreakDetector
from app.services.agents.guardrails.output_jailbreak_detector import OutputJailbreakDetector
from app.services.agents.guardrails.content_filter import ContentFilter
from app.services.agents.guardrails.pii_redactor import PIIRedactor

logger = logging.getLogger(__name__)

class GuardrailPolicyOrchestrator:
    """
    Orchestrates safety guardrails for inputs and outputs.
    Makes unified decisions (allow, redact, block, review).
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.jailbreak_in = JailbreakDetector()
        self.jailbreak_out = OutputJailbreakDetector()
        self.filter = ContentFilter()
        self.pii = PIIRedactor()

    async def check_input(self, run_id: uuid.UUID, tenant_id: str, content: str) -> Tuple[str, str]:
        """
        Runs guardrails on agent input.
        Returns (decision, reason).
        """
        is_jb, patterns = self.jailbreak_in.detect(content)
        if is_jb:
            await self._record_event(run_id, tenant_id, "jailbreak", "input", content, None, {"patterns": patterns})
            await self._record_decision(run_id, tenant_id, "block", f"Jailbreak detected: {patterns}")
            return "block", f"Jailbreak detected: {patterns}"

        has_secrets, secrets = self.filter.detect_secrets(content)
        if has_secrets:
            await self._record_event(run_id, tenant_id, "secret", "input", content, None, {"secrets": secrets})
            await self._record_decision(run_id, tenant_id, "block", "Secret detected in input")
            return "block", "Secret detected in input"

        return "allow", "All input guardrails passed"

    async def check_output(self, run_id: uuid.UUID, tenant_id: str, content: str) -> Tuple[str, str, str]:
        """
        Runs guardrails on agent output.
        Returns (decision, reason, sanitized_content).
        """
        sanitized_content = content
        
        is_jb, patterns = self.jailbreak_out.detect(content)
        if is_jb:
            await self._record_event(run_id, tenant_id, "policy_bypass", "model_output", content, None, {"patterns": patterns})
            await self._record_decision(run_id, tenant_id, "block", f"Policy bypass detected in output: {patterns}")
            return "block", f"Policy bypass detected in output: {patterns}", content

        has_secrets, secrets = self.filter.detect_secrets(content)
        if has_secrets:
            await self._record_event(run_id, tenant_id, "secret", "model_output", content, None, {"secrets": secrets})
            # For secrets in output, we block by default as redaction might be incomplete
            await self._record_decision(run_id, tenant_id, "block", "Secret leak detected in output")
            return "block", "Secret leak detected in output", content

        redacted_content, pii_count = self.pii.redact(content)
        if pii_count > 0:
            sanitized_content = redacted_content
            await self._record_event(run_id, tenant_id, "pii", "model_output", content, redacted_content, {"pii_count": pii_count})
            await self._record_decision(run_id, tenant_id, "redact", f"Redacted {pii_count} PII items")
            # We don't return block, just redacted
        
        return "allow" if pii_count == 0 else "redact", "Output guardrails passed", sanitized_content

    async def _record_event(self, run_id: uuid.UUID, tenant_id: str, g_type: str, point: str, raw: str, sanitized: str = None, meta: Dict = None):
        event = AgentGuardrailEvent(
            run_id=run_id,
            tenant_id=tenant_id,
            guardrail_type=g_type,
            detection_point=point,
            raw_content=raw,
            sanitized_content=sanitized,
            metadata_json=meta or {}
        )
        self.db.add(event)
        await self.db.flush()

    async def _record_decision(self, run_id: uuid.UUID, tenant_id: str, decision: str, reason: str):
        record = AgentGuardrailDecision(
            run_id=run_id,
            tenant_id=tenant_id,
            decision=decision,
            reason=reason
        )
        self.db.add(record)
        await self.db.flush()
