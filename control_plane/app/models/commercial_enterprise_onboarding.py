import uuid
from datetime import datetime

from app.db.base_class import Base
from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship


class EnterpriseCustomer(Base):
    __tablename__ = "enterprise_customers"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, index=True)
    contact_email = Column(String)
    tier = Column(String, default="pilot") # pilot, growth, enterprise
    created_at = Column(DateTime, default=datetime.utcnow)
    
    projects = relationship("EnterpriseOnboardingProject", back_populates="customer")

class EnterpriseOnboardingProject(Base):
    __tablename__ = "enterprise_onboarding_projects"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String, ForeignKey("enterprise_customers.id"))
    name = Column(String)
    status = Column(String, default="draft") # draft, discovery, deployment_ready, deployed, validation_ready, accepted, handed_over, support_active
    start_date = Column(DateTime, default=datetime.utcnow)
    target_date = Column(DateTime, nullable=True)
    
    config_snapshot = Column(JSON, default={}) # current environment config
    
    customer = relationship("EnterpriseCustomer", back_populates="projects")
    tasks = relationship("EnterpriseOnboardingTask", back_populates="project")

class EnterpriseOnboardingTask(Base):
    __tablename__ = "enterprise_onboarding_tasks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("enterprise_onboarding_projects.id"))
    title = Column(String)
    category = Column(String) # discovery, security, deployment, training, etc.
    status = Column(String, default="pending") # pending, in_progress, completed, blocked
    assigned_to = Column(String, nullable=True)
    due_date = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    
    project = relationship("EnterpriseOnboardingProject", back_populates="tasks")

class EnterpriseAcceptanceCheck(Base):
    __tablename__ = "enterprise_acceptance_checks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("enterprise_onboarding_projects.id"))
    criteria = Column(String)
    category = Column(String) # performance, security, reliability, functional
    is_passed = Column(Boolean, default=False)
    evidence_link = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

class EnterpriseHandoverReport(Base):
    __tablename__ = "enterprise_handover_reports"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("enterprise_onboarding_projects.id"))
    generated_at = Column(DateTime, default=datetime.utcnow)
    content_json = Column(JSON)
    artifact_path = Column(String, nullable=True)

class EnterpriseTrainingSession(Base):
    __tablename__ = "enterprise_training_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("enterprise_onboarding_projects.id"))
    session_name = Column(String)
    date = Column(DateTime)
    attendees_count = Column(Integer, default=0)
    status = Column(String, default="scheduled") # scheduled, completed, cancelled
