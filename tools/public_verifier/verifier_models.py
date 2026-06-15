from __future__ import annotations

from pydantic import BaseModel


class MerkleProofStep(BaseModel):
    sibling_hash: str
    is_right: bool


class MerkleInclusionProof(BaseModel):
    leaf_hash: str
    leaf_index: int
    steps: list[MerkleProofStep]
    root: str


class ReplayVerificationSummary(BaseModel):
    chain_valid: bool
    signature_valid: bool
    timestamp_mode: str | None = None


class TimestampSummary(BaseModel):
    signed_at: str | None = None


class WitnessSignature(BaseModel):
    witness_name: str
    witness_type: str
    public_key: str | None = None
    signature: str
    signature_algorithm: str
    signed_at: str


class WitnessQuorumSummary(BaseModel):
    quorum_status: str  # VALID, PARTIAL, INVALID
    required_signatures: int
    signatures_found: int
    external_witness_present: bool
    signatures: list[WitnessSignature] = []


class ConsistencyCheckpoint(BaseModel):
    checkpoint_type: str
    period_start: str
    period_end: str
    root_hash: str
    signed_checkpoint: str | None = None
    witness_summary: dict | None = None


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
    previous_timeline_root: str | None = None
    merkle_inclusion_proof: MerkleInclusionProof
    runtime_snapshot_hash: str | None = None
    model_manifest_hash: str | None = None
    replay_verification_summary: ReplayVerificationSummary | None = None
    timestamp_summary: TimestampSummary | None = None
    witness_quorum_summary: WitnessQuorumSummary | None = None
    policy_hash: str | None = None
    lineage_root_hash: str | None = None
    retrieval_sent_hash: str | None = None
    chunk_participants: list[dict] | None = None
    document_participants: list[str] | None = None
    lineage_chain: list[dict] | None = None
    created_at: str | None = None


class VerificationCheck(BaseModel):
    name: str
    status: str  # VALID, INVALID, WARNING, SKIP
    message: str


class VerificationReport(BaseModel):
    overall_status: str
    proof_hash: str
    timeline_root: str
    verified_at: str
    checks: list[VerificationCheck]
    warnings: list[str] = []
    errors: list[str] = []
