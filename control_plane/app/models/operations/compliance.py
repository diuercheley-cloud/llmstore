import uuid
from datetime import datetime

from app.db.base_class import Base
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship


class ComplianceFramework(Base):
    __tablename__ = "compliance_frameworks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, index=True) # SOC2, ISO27001
    description = Column(Text)
    version = Column(String)
    
    controls = relationship("ComplianceControl", back_populates="framework")

class ComplianceControl(Base):
    __tablename__ = "compliance_controls"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    framework_id = Column(String, ForeignKey("compliance_frameworks.id"))
    code = Column(String, index=True) # CC1.1, A.5.1
    title = Column(String)
    description = Column(Text)
    category = Column(String) # Security, Privacy, etc.
    status = Column(String, default="not_started") # not_started, partial, implemented, exempt
    
    framework = relationship("ComplianceFramework", back_populates="controls")
    evidence_items = relationship("ComplianceEvidenceItem", back_populates="control")
    tests = relationship("ComplianceControlTest", back_populates="control")

class ComplianceEvidenceItem(Base):
    __tablename__ = "compliance_evidence_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    control_id = Column(String, ForeignKey("compliance_controls.id"))
    name = Column(String)
    description = Column(Text)
    source_type = Column(String) # auto_script, manual_upload, system_log
    content_reference = Column(String) # file path or hash
    collected_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="valid") # valid, expired, rejected
    
    control = relationship("ComplianceControl", back_populates="evidence_items")

class ComplianceControlTest(Base):
    __tablename__ = "compliance_control_tests"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    control_id = Column(String, ForeignKey("compliance_controls.id"))
    name = Column(String)
    last_run_at = Column(DateTime)
    result = Column(String) # passed, failed, warning
    findings = Column(Text)
    
    control = relationship("ComplianceControl", back_populates="tests")

class ComplianceRiskItem(Base):
    __tablename__ = "compliance_risk_register"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String)
    description = Column(Text)
    impact = Column(Integer) # 1-5
    likelihood = Column(Integer) # 1-5
    inherent_risk_score = Column(Integer)
    mitigation_strategy = Column(Text)
    residual_risk_score = Column(Integer)
    status = Column(String, default="active") # active, closed, monitoring

class CompliancePolicyDocument(Base):
    __tablename__ = "compliance_policy_documents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String)
    version = Column(String)
    status = Column(String, default="draft") # draft, reviewed, approved, obsolete
    content_hash = Column(String)
    last_reviewed_at = Column(DateTime)
    next_review_at = Column(DateTime)
