import uuid
from datetime import datetime, UTC

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class CommercialRAGVault(Base):
    __tablename__ = "commercial_rag_vaults"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(128), nullable=True, index=True, default="default")
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True)
    vault_name = Column(String(128), nullable=False)
    
    vault_mode = Column(String(64), default="standard") # standard|confidential
    retrieval_mode = Column(String(64), default="standard") # standard|hybrid|verifiable
    
    is_encrypted = Column(Boolean, default=True)
    encryption_required = Column(Boolean, default=False)
    encryption_key_hash = Column(String(128), nullable=True) # Proof of tenant isolation
    
    retention_policy_days = Column(Integer, default=30)
    strict_policy_enforcement = Column(Boolean, default=True)
    immutable_audit_enabled = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

class CommercialRAGDocument(Base):
    __tablename__ = "commercial_rag_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vault_id = Column(UUID(as_uuid=True), ForeignKey("commercial_rag_vaults.id"), nullable=False)
    
    document_hash = Column(String(128), nullable=False, index=True) # Content hash
    document_title = Column(String(255), nullable=True)
    metadata_encrypted = Column(JSON, nullable=True) # Sanitized or encrypted metadata
    metadata_json = Column(JSON, nullable=True)
    
    classification = Column(String(64), default="internal")
    classification_level = Column(String(64), default="confidential") # internal|confidential|restricted
    status = Column(String(32), default="active") # active|archived|deleted
    ingestion_status = Column(String(32), default="pending")
    source_type = Column(String(64), default="manual")
    
    provenance_hash = Column(String(128), nullable=True)
    signed_manifest_hash = Column(String(128), nullable=True)
    legal_hold = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    expires_at = Column(DateTime, nullable=True)

class CommercialRAGChunk(Base):
    __tablename__ = "commercial_rag_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("commercial_rag_documents.id"), nullable=False)
    
    chunk_hash = Column(String(128), nullable=False, index=True) # Never plaintext
    chunk_index = Column(Integer, nullable=False)
    
    embedding_hash = Column(String(128), nullable=True)
    embedding_metadata_encrypted = Column(JSON, nullable=True)
    acl_json = Column(JSON, nullable=True)
    encrypted_payload = Column(Text, nullable=True)
    poisoned_flag = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

class CommercialRetrievalReceipt(Base):
    __tablename__ = "commercial_retrieval_receipts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vault_id = Column(UUID(as_uuid=True), ForeignKey("commercial_rag_vaults.id"), nullable=False)
    session_id = Column(String(128), nullable=False, index=True) # Associated inference session
    
    query_hash = Column(String(128), nullable=False)
    retrieved_chunk_hashes = Column(JSON, nullable=False) # List of chunk hashes
    
    receipt_hash = Column(String(128), nullable=False, index=True)
    signature = Column(String(256), nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

class CommercialRetrievalPolicyViolation(Base):
    __tablename__ = "commercial_retrieval_policy_violations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vault_id = Column(UUID(as_uuid=True), ForeignKey("commercial_rag_vaults.id"), nullable=False)
    
    session_id = Column(String(128), nullable=False)
    query_hash = Column(String(128), nullable=False)
    
    violation_type = Column(String(64), nullable=False) # cross_tenant|classification_mismatch|expired_document
    action_taken = Column(String(32), default="blocked")
    
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

class CommercialRAGLegalHold(Base):
    __tablename__ = "commercial_rag_legal_holds"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(128), nullable=True, index=True, default="default")
    case_id = Column(String(128), nullable=True, index=True)
    vault_id = Column(UUID(as_uuid=True), ForeignKey("commercial_rag_vaults.id"), nullable=True, index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("commercial_rag_documents.id"), nullable=True, index=True)
    hold_reason = Column(Text, nullable=True)
    active = Column(Boolean, default=True)
    
    reason = Column(Text, nullable=True)
    status = Column(String(32), default="active") # active|released
    
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    released_at = Column(DateTime, nullable=True)

class CommercialRAGPoisoningAlert(Base):
    __tablename__ = "commercial_rag_poisoning_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(128), nullable=True, index=True, default="default")
    vault_id = Column(UUID(as_uuid=True), ForeignKey("commercial_rag_vaults.id"), nullable=True, index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("commercial_rag_documents.id"), nullable=True)
    
    alert_type = Column(String(64))
    severity = Column(String(32))
    summary = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    resolved = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

class CommercialRAGRetrievalAudit(Base):
    __tablename__ = "commercial_rag_retrieval_audits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(128), nullable=True, index=True, default="default")
    vault_id = Column(UUID(as_uuid=True), ForeignKey("commercial_rag_vaults.id"), nullable=True, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True, index=True)

    request_hash = Column(String(128), nullable=True, index=True)
    retrieval_hash = Column(String(128), nullable=True, index=True)
    user_identity_hash = Column(String(128), nullable=True, index=True)
    retrieved_chunk_count = Column(Integer, nullable=True, default=0)
    policy_result = Column(String(64), nullable=True, index=True)
    model_id = Column(String(255), nullable=True, index=True)
    immutable_hash = Column(String(128), nullable=True, index=True)
    
    query_hash = Column(String(128), nullable=True)
    results_hashes = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

class CommercialRAGAccessPolicy(Base):
    __tablename__ = "commercial_rag_access_policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vault_id = Column(UUID(as_uuid=True), ForeignKey("commercial_rag_vaults.id"), nullable=False)
    
    policy_name = Column(String(128), nullable=True)
    policy_mode = Column(String(32), default="audit") # enforce|audit|disabled
    
    allow_cross_tenant = Column(Boolean, default=False)
    require_abac = Column(Boolean, default=False)
    require_signed_document = Column(Boolean, default=False)
    require_confidential_runtime = Column(Boolean, default=False)
    require_trusted_model = Column(Boolean, default=False)
    
    max_context_chunks = Column(Integer, default=5)
    
    principal_type = Column(String(32)) # user|role|api_key
    principal_id = Column(String(128))
    
    permissions = Column(JSON) # ["read", "write", "admin"]
    
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
