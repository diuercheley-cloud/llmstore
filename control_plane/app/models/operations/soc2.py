import uuid
from datetime import datetime, UTC

from app.db.base import Base
from sqlalchemy import JSON, Column, DateTime, String, Text


class SOC2ControlReview(Base):
    __abstract__ = True
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    owner = Column(String)
    reviewer = Column(String)
    period_start = Column(DateTime)
    period_end = Column(DateTime)
    evidence_links = Column(JSON)
    findings = Column(Text)
    exceptions = Column(Text)
    remediation_actions = Column(Text)
    approval_status = Column(String, default="pending") # pending, approved, rejected
    approved_at = Column(DateTime)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

class SOC2AccessReview(SOC2ControlReview):
    __tablename__ = "soc2_access_reviews"

class SOC2ChangeReview(SOC2ControlReview):
    __tablename__ = "soc2_change_reviews"

class SOC2IncidentReview(SOC2ControlReview):
    __tablename__ = "soc2_incident_reviews"

class SOC2VendorReview(SOC2ControlReview):
    __tablename__ = "soc2_vendor_reviews"

class SOC2BackupRestoreReview(SOC2ControlReview):
    __tablename__ = "soc2_backup_restore_reviews"

class SOC2ControlException(Base):
    __tablename__ = "soc2_control_exceptions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    control_id = Column(String)
    reason = Column(Text)
    owner = Column(String)
    expiration_date = Column(DateTime)
    status = Column(String, default="active") # active, expired, closed
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
