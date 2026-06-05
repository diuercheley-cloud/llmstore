from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import uuid

class ComplianceFramework(str, Enum):
    SOC2 = "SOC2"
    ISO27001 = "ISO27001"
    GDPR = "GDPR"
    LGPD = "LGPD"

class EvidenceType(str, Enum):
    POLICY_DECISION = "policy_decision"
    AUDIT_LOG = "audit_log"
    ACCESS_LOG = "access_log"
    ATTESTATION = "attestation"
    BACKUP_VERIFICATION = "backup_verification"
    EVAL_REPORT = "eval_report"
    INCIDENT_RECORD = "incident_record"

class EvidenceItem(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    framework: ComplianceFramework
    control_id: str
    evidence_type: EvidenceType
    source: str
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "collected"
    content_hash: str
    redaction_status: str = "redacted"
    data: Dict[str, Any] = Field(default_factory=dict)

class EvidenceCollectionRequest(BaseModel):
    frameworks: List[ComplianceFramework] = Field(default_factory=lambda: [f for f in ComplianceFramework])
    dry_run: bool = False

class EvidenceExportFormat(str, Enum):
    JSON = "json"
    CSV = "csv"
    MARKDOWN = "markdown"
