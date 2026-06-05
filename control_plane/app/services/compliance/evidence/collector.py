import hashlib
import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.schemas.compliance_evidence import ComplianceFramework, EvidenceItem, EvidenceType
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class ComplianceEvidenceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def collect_evidence(self, frameworks: List[ComplianceFramework]) -> List[EvidenceItem]:
        """
        Gathers evidence across multiple frameworks and sources.
        """
        logger.info(f"Starting compliance evidence collection for: {frameworks}")
        collected_items = []

        # Simulated collection logic for each framework
        for fw in frameworks:
            if fw == ComplianceFramework.SOC2:
                collected_items.extend(await self._collect_soc2())
            elif fw == ComplianceFramework.ISO27001:
                collected_items.extend(await self._collect_iso27001())
            elif fw == ComplianceFramework.GDPR:
                collected_items.extend(await self._collect_gdpr())
            elif fw == ComplianceFramework.LGPD:
                collected_items.extend(await self._collect_lgpd())

        logger.info(f"Collected {len(collected_items)} evidence items.")
        return collected_items

    async def _collect_soc2(self) -> List[EvidenceItem]:
        return [
            self._create_evidence(
                ComplianceFramework.SOC2, "CC6.1", EvidenceType.ACCESS_LOG,
                "RBAC Policy Logs", {"entries": ["User A accessed Node X", "User B denied"]}
            ),
            self._create_evidence(
                ComplianceFramework.SOC2, "CC7.1", EvidenceType.AUDIT_LOG,
                "System Audit Trail", {"events": ["Config changed by admin", "Model Y deployed"]}
            )
        ]

    async def _collect_iso27001(self) -> List[EvidenceItem]:
        return [
            self._create_evidence(
                ComplianceFramework.ISO27001, "A.12.3", EvidenceType.BACKUP_VERIFICATION,
                "Backup Verification Report", {"last_verified": datetime.utcnow().isoformat(), "status": "success"}
            ),
            self._create_evidence(
                ComplianceFramework.ISO27001, "A.14.2", EvidenceType.POLICY_DECISION,
                "Secure Development Policy", {"version": "2.1", "approved_by": "CTO"}
            )
        ]

    async def _collect_gdpr(self) -> List[EvidenceItem]:
        return [
            self._create_evidence(
                ComplianceFramework.GDPR, "Art. 32", EvidenceType.ATTESTATION,
                "Data Encryption Attestation", {"method": "AES-256-GCM", "scope": "All PII"}
            ),
            self._create_evidence(
                ComplianceFramework.GDPR, "Art. 35", EvidenceType.EVAL_REPORT,
                "DPIA Summary (Draft)", {"status": "in_progress", "risk_level": "medium"}
            )
        ]

    async def _collect_lgpd(self) -> List[EvidenceItem]:
        return [
            self._create_evidence(
                ComplianceFramework.LGPD, "Art. 46", EvidenceType.INCIDENT_RECORD,
                "Incident Log Placeholder", {"incidents": 0, "period": "Q2 2026"}
            )
        ]

    def _create_evidence(self, framework: ComplianceFramework, control_id: str, 
                         etype: EvidenceType, source: str, data: Dict[str, Any]) -> EvidenceItem:
        # Redact data
        redacted_data = self._redact_sensitive_data(data)
        
        # Calculate Hash
        content_str = json.dumps(redacted_data, sort_keys=True)
        content_hash = hashlib.sha256(content_str.encode()).hexdigest()
        
        return EvidenceItem(
            framework=framework,
            control_id=control_id,
            evidence_type=etype,
            source=source,
            content_hash=content_hash,
            data=redacted_data
        )

    def _redact_sensitive_data(self, data: Any) -> Any:
        if isinstance(data, dict):
            # Handle password key specifically in dicts
            return {k: ("[REDACTED_PASSWORD]" if k.lower() == "password" else self._redact_sensitive_data(v)) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._redact_sensitive_data(i) for i in data]
        elif isinstance(data, str):
            # Mask API keys, tokens, and secrets
            patterns = [
                (r'sk-[a-zA-Z0-9]{20,}', '[REDACTED_API_KEY]'),
                (r'token:[a-zA-Z0-9.\-_]{20,}', '[REDACTED_TOKEN]'),
                (r'(?i)password\s*:\s*[^\s]+', 'password: [REDACTED]')
            ]
            redacted = data
            for pattern, repl in patterns:
                redacted = re.sub(pattern, repl, redacted)
            return redacted
        return data

    def format_as_markdown(self, items: List[EvidenceItem]) -> str:
        md = "# Compliance Evidence Support Report\n\n"
        md += f"Generated at: {datetime.now().isoformat()}\n\n"
        
        current_fw = None
        for item in sorted(items, key=lambda x: x.framework):
            fw_name = item.framework.value if hasattr(item.framework, "value") else str(item.framework)
            if fw_name != current_fw:
                current_fw = fw_name
                md += f"## Framework: {current_fw}\n\n"
            
            md += f"### Control {item.control_id} - {item.source}\n"
            md += f"- **Type**: {item.evidence_type.value if hasattr(item.evidence_type, 'value') else item.evidence_type}\n"
            md += f"- **Collected at**: {item.collected_at}\n"
            md += f"- **Hash**: `{item.content_hash}`\n"
            md += f"- **Data**:\n```json\n{json.dumps(item.data, indent=2)}\n```\n\n"
            
        return md
