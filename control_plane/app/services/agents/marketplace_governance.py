"""
Marketplace Publishing Governance.
Approval workflow, security scanning, and validation for agent marketplace submissions.
"""

import asyncio
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class SubmissionStatus(str, Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    SECURITY_SCANNING = "security_scanning"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"


class ReviewSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class ReviewFinding:
    severity: ReviewSeverity
    category: str
    title: str
    description: str
    location: Optional[str] = None
    recommendation: Optional[str] = None


@dataclass
class Submission:
    agent_id: str
    version: str
    submitted_by: str
    status: SubmissionStatus = SubmissionStatus.DRAFT
    id: str = ""
    findings: List[ReviewFinding] = field(default_factory=list)
    reviewer_notes: Optional[str] = None
    reviewed_by: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now(UTC).isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at


class MarketplaceGovernanceService:
    """
    Governance workflow for marketplace agent publishing.
    Enforces security scanning, policy validation, and approval gates.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._submissions: Dict[str, Submission] = {}

    async def create_submission(self, agent_id: str, version: str, submitted_by: str) -> Submission:
        sub = Submission(agent_id=agent_id, version=version, submitted_by=submitted_by)
        self._submissions[sub.id] = sub
        logger.info("Marketplace submission created: %s (agent=%s, v=%s)", sub.id, agent_id, version)
        return sub

    async def submit_for_review(self, submission_id: str) -> Submission:
        sub = self._get_submission(submission_id)
        sub.status = SubmissionStatus.PENDING_REVIEW
        sub.updated_at = datetime.now(UTC).isoformat()
        logger.info("Submission %s submitted for review", submission_id)
        return sub

    async def run_security_scan(self, submission_id: str) -> Submission:
        sub = self._get_submission(submission_id)
        sub.status = SubmissionStatus.SECURITY_SCANNING

        await asyncio.sleep(0.1)

        findings = await self._scan_agent(sub.agent_id)
        sub.findings.extend(findings)

        critical = any(f.severity == ReviewSeverity.CRITICAL for f in findings)
        high = any(f.severity == ReviewSeverity.HIGH for f in findings)

        if critical or high:
            sub.status = SubmissionStatus.REJECTED
            sub.reviewer_notes = f"Security scan failed: {len(findings)} findings (critical={sum(1 for f in findings if f.severity == ReviewSeverity.CRITICAL)}, high={sum(1 for f in findings if f.severity == ReviewSeverity.HIGH)})"
        else:
            sub.status = SubmissionStatus.APPROVED
            sub.reviewer_notes = f"Security scan passed: {len(findings)} low/info findings"

        sub.updated_at = datetime.now(UTC).isoformat()
        logger.info("Security scan for %s: status=%s, findings=%d", submission_id, sub.status, len(findings))
        return sub

    async def approve_submission(self, submission_id: str, reviewer: str, notes: Optional[str] = None) -> Submission:
        sub = self._get_submission(submission_id)
        sub.status = SubmissionStatus.APPROVED
        sub.reviewed_by = reviewer
        if notes:
            sub.reviewer_notes = notes
        sub.updated_at = datetime.now(UTC).isoformat()
        logger.info("Submission %s approved by %s", submission_id, reviewer)
        return sub

    async def reject_submission(self, submission_id: str, reviewer: str, reason: str) -> Submission:
        sub = self._get_submission(submission_id)
        sub.status = SubmissionStatus.REJECTED
        sub.reviewed_by = reviewer
        sub.reviewer_notes = reason
        sub.updated_at = datetime.now(UTC).isoformat()
        logger.info("Submission %s rejected by %s: %s", submission_id, reviewer, reason)
        return sub

    async def publish_submission(self, submission_id: str) -> Submission:
        sub = self._get_submission(submission_id)
        if sub.status != SubmissionStatus.APPROVED:
            raise ValueError(f"Cannot publish submission in status '{sub.status}'. Must be 'approved'.")
        sub.status = SubmissionStatus.PUBLISHED
        sub.updated_at = datetime.now(UTC).isoformat()
        logger.info("Submission %s published to marketplace", submission_id)
        return sub

    def get_submission(self, submission_id: str) -> Optional[Submission]:
        return self._submissions.get(submission_id)

    def list_submissions(self, status: Optional[SubmissionStatus] = None) -> List[Submission]:
        if status:
            return [s for s in self._submissions.values() if s.status == status]
        return list(self._submissions.values())

    def _get_submission(self, submission_id: str) -> Submission:
        sub = self._submissions.get(submission_id)
        if not sub:
            raise ValueError(f"Submission not found: {submission_id}")
        return sub

    async def _scan_agent(self, agent_id: str) -> List[ReviewFinding]:
        findings = []

        from app.models.agents import AgentDefinition
        result = await self.db.execute(
            select(AgentDefinition).where(AgentDefinition.id == agent_id)
        )
        agent = result.scalar_one_or_none()

        if not agent:
            findings.append(ReviewFinding(
                severity=ReviewSeverity.CRITICAL,
                category="agent_exists",
                title="Agent not found",
                description=f"Agent {agent_id} does not exist in the registry.",
            ))
            return findings

        if not agent.system_prompt or len(agent.system_prompt.strip()) < 10:
            findings.append(ReviewFinding(
                severity=ReviewSeverity.MEDIUM,
                category="prompt_quality",
                title="System prompt too short",
                description="Agent system prompt is empty or too short (< 10 chars).",
                recommendation="Provide a meaningful system prompt that defines the agent's purpose.",
            ))

        if agent.tools and len(agent.tools) > 0:
            for tool in agent.tools:
                if isinstance(tool, str) and ("shell" in tool.lower() or "exec" in tool.lower()):
                    findings.append(ReviewFinding(
                        severity=ReviewSeverity.HIGH,
                        category="dangerous_tool",
                        title=f"Dangerous tool: {tool}",
                        description=f"Agent uses potentially dangerous tool '{tool}'.",
                        recommendation="Restrict shell/exec tools or require human approval.",
                        location=f"tools.{tool}",
                    ))

        if agent.memory and agent.memory == "long_term":
            findings.append(ReviewFinding(
                severity=ReviewSeverity.LOW,
                category="data_privacy",
                title="Long-term memory enabled",
                description="Agent uses long-term memory. Ensure data privacy and consent are configured.",
                recommendation="Configure memory retention and consent policies.",
            ))

        return findings


class MarketplacePublishingAPI:
    """
    API layer for marketplace publishing governance.
    """

    def __init__(self, governance: MarketplaceGovernanceService):
        self.governance = governance

    async def submit_agent(self, agent_id: str, version: str, submitted_by: str) -> dict:
        sub = await self.governance.create_submission(agent_id, version, submitted_by)
        await self.governance.submit_for_review(sub.id)
        sub = await self.governance.run_security_scan(sub.id)
        return asdict(sub)

    async def review_submission(self, submission_id: str, reviewer: str, action: str, reason: Optional[str] = None) -> dict:
        if action == "approve":
            sub = await self.governance.approve_submission(submission_id, reviewer, reason)
        elif action == "reject":
            sub = await self.governance.reject_submission(submission_id, reviewer, reason or "No reason provided")
        else:
            raise ValueError(f"Unknown action: {action}")
        return asdict(sub)

    async def publish(self, submission_id: str) -> dict:
        sub = await self.governance.publish_submission(submission_id)
        return asdict(sub)
