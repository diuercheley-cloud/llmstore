
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class MerkleProofStep(BaseModel):
    sibling_hash: str
    is_right: bool

class MerkleInclusionProof(BaseModel):
    leaf_hash: str
    leaf_index: int
    steps: List[MerkleProofStep]
    root: str

class ReplayVerificationSummary(BaseModel):
    chain_valid: bool
    signature_valid: bool
    timestamp_mode: Optional[str] = None

class TimestampSummary(BaseModel):
    signed_at: Optional[str] = None

class WitnessSignature(BaseModel):
    witness_name: str
    witness_type: str
    public_key: Optional[str] = None
    signature: str
    signature_algorithm: str
    signed_at: str

class WitnessQuorumSummary(BaseModel):
    quorum_status: str # VALID, PARTIAL, INVALID
    required_signatures: int
    signatures_found: int
    external_witness_present: bool
    signatures: List[WitnessSignature] = []

class ConsistencyCheckpoint(BaseModel):
    checkpoint_type: str
    period_start: str
    period_end: str
    root_hash: str
    signed_checkpoint: Optional[str] = None
    witness_summary: Optional[dict] = None

class SplitViewAlert(BaseModel):
    alert_type: str
    severity: str
    expected_hash: str
    observed_hash: str
    summary: str
    created_at: str

class ExecutionProof(BaseModel):
    proof_type: str
    proof_hash: str
    verification_status: str
    timeline_root: str
    previous_timeline_root: Optional[str] = None
    merkle_inclusion_proof: MerkleInclusionProof
    runtime_snapshot_hash: Optional[str] = None
    model_manifest_hash: Optional[str] = None
    replay_verification_summary: Optional[ReplayVerificationSummary] = None
    timestamp_summary: Optional[TimestampSummary] = None
    witness_quorum_summary: Optional[WitnessQuorumSummary] = None
    policy_hash: Optional[str] = None
    lineage_root_hash: Optional[str] = None
    retrieval_sent_hash: Optional[str] = None
    chunk_participants: Optional[List[dict]] = None
    document_participants: Optional[List[str]] = None
    lineage_chain: Optional[List[dict]] = None
    created_at: Optional[str] = None

class VerificationCheck(BaseModel):
    name: str
    status: str  # VALID, INVALID, WARNING, SKIP
    message: str

class VerificationReport(BaseModel):
    overall_status: str
    proof_hash: str
    timeline_root: str
    verified_at: str
    checks: List[VerificationCheck]
    warnings: List[str] = []
    errors: List[str] = []
