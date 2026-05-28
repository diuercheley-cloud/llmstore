import uuid
from datetime import datetime
from typing import Optional, Any, List
from sqlalchemy import Column, String, DateTime, JSON, Boolean, ForeignKey, Integer, Text, Float
from sqlalchemy.dialects.postgresql import UUID
from ..db.base import Base

class CommercialRAGVault(Base):
    __tablename__ = "commercial_rag_vaults"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(128), nullable=False, index=True)
    vault_name = Column(String(128), nullable=False)
    
    is_encrypted = Column(Boolean, default=True)
    encryption_key_hash = Column(String(128), nullable=True) # Proof of tenant isolation
    
    retention_policy_days = Column(Integer, default=30)
    strict_policy_enforcement = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CommercialRAGDocument(Base):
    __tablename__ = "commercial_rag_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vault_id = Column(UUID(as_uuid=True), ForeignKey("commercial_rag_vaults.id"), nullable=False)
    
    document_hash = Column(String(128), nullable=False, index=True) # Content hash
    metadata_encrypted = Column(JSON, nullable=True) # Sanitized or encrypted metadata
    
    classification_level = Column(String(64), default="confidential") # internal|confidential|restricted
    status = Column(String(32), default="active") # active|archived|deleted
    
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

class CommercialRAGChunk(Base):
    __tablename__ = "commercial_rag_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("commercial_rag_documents.id"), nullable=False)
    
    chunk_hash = Column(String(128), nullable=False, index=True) # Never plaintext
    chunk_index = Column(Integer, nullable=False)
    
    embedding_metadata_encrypted = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

class CommercialRetrievalReceipt(Base):
    __tablename__ = "commercial_retrieval_receipts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vault_id = Column(UUID(as_uuid=True), ForeignKey("commercial_rag_vaults.id"), nullable=False)
    session_id = Column(String(128), nullable=False, index=True) # Associated inference session
    
    query_hash = Column(String(128), nullable=False)
    retrieved_chunk_hashes = Column(JSON, nullable=False) # List of chunk hashes
    
    receipt_hash = Column(String(128), nullable=False, index=True)
    signature = Column(String(256), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

class CommercialRetrievalPolicyViolation(Base):
    __tablename__ = "commercial_retrieval_policy_violations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vault_id = Column(UUID(as_uuid=True), ForeignKey("commercial_rag_vaults.id"), nullable=False)
    
    session_id = Column(String(128), nullable=False)
    query_hash = Column(String(128), nullable=False)
    
    violation_type = Column(String(64), nullable=False) # cross_tenant|classification_mismatch|expired_document
    action_taken = Column(String(32), default="blocked")
    
    created_at = Column(DateTime, default=datetime.utcnow)

class CommercialRAGLegalHold(Base):
    __tablename__ = "commercial_rag_legal_holds"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(128), nullable=False, index=True)
    case_id = Column(String(128), nullable=False, index=True)
    
    reason = Column(Text, nullable=True)
    status = Column(String(32), default="active") # active|released
    
    created_at = Column(DateTime, default=datetime.utcnow)
    released_at = Column(DateTime, nullable=True)

class CommercialRAGPoisoningAlert(Base):
    __tablename__ = "commercial_rag_poisoning_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(128), nullable=False, index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("commercial_rag_documents.id"), nullable=True)
    
    alert_type = Column(String(64))
    severity = Column(String(32))
    metadata_json = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

class CommercialRAGRetrievalAudit(Base):
    __tablename__ = "commercial_rag_retrieval_audits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(128), nullable=False, index=True)
    
    query_hash = Column(String(128))
    results_hashes = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow)

class CommercialRAGAccessPolicy(Base):
    __tablename__ = "commercial_rag_access_policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vault_id = Column(UUID(as_uuid=True), ForeignKey("commercial_rag_vaults.id"), nullable=False)
    
    principal_type = Column(String(32)) # user|role|api_key
    principal_id = Column(String(128))
    
    permissions = Column(JSON) # ["read", "write", "admin"]
    
    created_at = Column(DateTime, default=datetime.utcnow)
