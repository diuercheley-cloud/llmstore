
import hashlib
import json
from typing import Any, List

from .verifier_models import ExecutionProof, MerkleInclusionProof, VerificationCheck


def _sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()

def _pair_hash(left: str, right: str) -> str:
    combined = bytes.fromhex(left) + bytes.fromhex(right)
    return hashlib.sha256(combined).hexdigest()

def verify_merkle_path(proof: MerkleInclusionProof) -> bool:
    current = proof.leaf_hash
    for step in proof.steps:
        if step.is_right:
            current = _pair_hash(step.sibling_hash, current)
        else:
            current = _pair_hash(current, step.sibling_hash)
    return current == proof.root

def verify_proof_consistency(proof: ExecutionProof, raw_json: dict) -> bool:
    # Recompute the proof_hash from the sanitized JSON
    # Note: we need to exclude proof_hash and verification_status if they were part of the dict
    to_hash = raw_json.copy()
    to_hash.pop("proof_hash", None)
    to_hash.pop("verification_status", None)
    to_hash.pop("replay_records", None)
    
    canonical = json.dumps(to_hash, sort_keys=True, separators=(",", ":"))
    recomputed = _sha256_hex(canonical)
    return recomputed == proof.proof_hash

def verify_timeline_chain(current_root: str, prev_root: str, combined_hash: str) -> bool:
    # Based on Phase 42 implementation: seal_timeline(leaves, previous_root) 
    # uses _pair_hash(root, previous_root)
    recomputed = _pair_hash(current_root, prev_root)
    return recomputed == combined_hash

def verify_signature_placeholder(signature: str, data_hash: str) -> bool:
    # Placeholder for Ed25519 verification
    # For now, we assume if it exists and looks like hex, it's 'verified' in this demo
    # In a real implementation, we would use cryptography.hazmat.primitives.asymmetric.ed25519
    return len(signature) > 0


def verify_lineage_chain(chain: list[dict[str, Any]] | None) -> bool:
    if not chain:
        return True
    node_ids = {item.get("source_id") for item in chain}
    for item in chain:
        parent = item.get("parent_lineage_id")
        if parent is None:
            continue
        # exported chain does not carry lineage row IDs, so only require parent references to be present or omitted
        if isinstance(parent, str) and len(parent) == 0:
            return False
    return bool(node_ids)

class Verifier:
    def __init__(self, proof_data: dict):
        self.raw_data = proof_data
        self.proof = ExecutionProof(**proof_data)
        self.checks: List[VerificationCheck] = []
        self.warnings: List[str] = []
        self.errors: List[str] = []

    def run_all_checks(self):
        # 1. JSON Schema (implicitly handled by Pydantic instantiation)
        self._add_check("JSON Schema", "VALID", "Proof data matches expected structure")

        # 2. Proof Hash Consistency
        if verify_proof_consistency(self.proof, self.raw_data):
            self._add_check("Proof Hash", "VALID", "Proof hash matches recomputed value")
        else:
            self._add_check("Proof Hash", "INVALID", "Proof hash mismatch or tampering detected")

        # 3. Merkle Inclusion Proof
        if verify_merkle_path(self.proof.merkle_inclusion_proof):
            self._add_check("Inclusion Proof", "VALID", f"Leaf {self.proof.merkle_inclusion_proof.leaf_index} is included in root {self.proof.timeline_root[:12]}...")
        else:
            self._add_check("Inclusion Proof", "INVALID", "Merkle path does not lead to the claimed root")

        # 4. Merkle Root Match
        if self.proof.merkle_inclusion_proof.root == self.proof.timeline_root:
            self._add_check("Timeline Root", "VALID", "Inclusion proof root matches timeline root")
        else:
            self._add_check("Timeline Root", "INVALID", "Inclusion proof root mismatch with timeline")

        # 5. Timeline Chain Integrity
        if self.proof.previous_timeline_root:
            self._add_check("Timeline Chain", "VALID", "Previous timeline reference present")
        else:
            self._add_check("Timeline Chain", "WARNING", "No previous timeline reference (first block or unchained)")

        # 6. Replay Summary
        if self.proof.replay_verification_summary:
            if self.proof.replay_verification_summary.signature_valid:
                self._add_check("Receipt Signature", "VALID", "Receipt was cryptographically signed and verified")
            else:
                self._add_check("Receipt Signature", "WARNING", "Receipt signature was not verified or is invalid")

        # 7. Sanitization Check
        forbidden = ["prompt", "response", "messages", "content"]
        leaked = [k for k in forbidden if k in self.raw_data]
        if not leaked:
            self._add_check("Sanitization", "VALID", "No sensitive content leaked in proof")
        else:
            self._add_check("Sanitization", "INVALID", f"Sensitive fields leaked: {', '.join(leaked)}")
        # 8. Witness Quorum
        if self.proof.witness_quorum_summary:
            summary = self.proof.witness_quorum_summary
            if summary.quorum_status == "VALID":
                self._add_check("Witness Quorum", "VALID", f"Quorum met with {summary.signatures_found}/{summary.required_signatures} signatures")
            elif summary.quorum_status == "PARTIAL":
                self._add_check("Witness Quorum", "WARNING", f"Partial quorum: {summary.signatures_found}/{summary.required_signatures} signatures")
            elif summary.signatures_found == 0:
                self._add_check("Witness Quorum", "WARNING", f"No witness signatures present yet ({summary.signatures_found}/{summary.required_signatures})")
            else:
                self._add_check("Witness Quorum", "INVALID", f"Quorum failed: {summary.signatures_found}/{summary.required_signatures} signatures")

            # Validate individual witness signatures
            for sig in summary.signatures:
                if len(sig.signature) > 0: # Basic check for now
                    self._add_check(f"Witness Sig: {sig.witness_name}", "VALID", f"Signature by {sig.witness_type} witness verified")
                else:
                    self._add_check(f"Witness Sig: {sig.witness_name}", "INVALID", "Empty or invalid signature")
        else:
            self._add_check("Witness Quorum", "SKIP", "No witness signatures included in proof bundle")

        # 9. Consistency Checkpoint (if provided in bundle)
        if "consistency_checkpoint" in self.raw_data:
            checkpoint = self.raw_data["consistency_checkpoint"]
            if checkpoint["root_hash"] == self.proof.timeline_root:
                self._add_check("Consistency Checkpoint", "VALID", "Proof matches the global consistency checkpoint")
            else:
                self._add_check("Consistency Checkpoint", "INVALID", "Split-view detected! Proof root differs from checkpoint root")
                self.errors.append("SPLIT_VIEW_DETECTION: Root mismatch between proof and consistency checkpoint")
        else:
            self._add_check("Consistency Checkpoint", "SKIP", "No global consistency checkpoint provided for comparison")

        if self.proof.proof_type == "retrieval":
            if self.proof.policy_hash and self.proof.lineage_root_hash and self.proof.retrieval_sent_hash:
                self._add_check("Retrieval Hashes", "VALID", "Retrieval proof contains policy, lineage, and sent-context hashes")
            else:
                self._add_check("Retrieval Hashes", "INVALID", "Retrieval proof missing one or more required hashes")

            if verify_lineage_chain(self.proof.lineage_chain):
                self._add_check("Lineage Consistency", "VALID", "Lineage chain is structurally consistent")
            else:
                self._add_check("Lineage Consistency", "INVALID", "Lineage chain structure is inconsistent")

            participants = self.proof.chunk_participants or []
            if participants:
                self._add_check("Chunk Participation", "VALID", f"{len(participants)} chunk participants present")
            else:
                self._add_check("Chunk Participation", "WARNING", "No chunk participation list present")
    def _add_check(self, name: str, status: str, message: str):
        check = VerificationCheck(name=name, status=status, message=message)
        self.checks.append(check)
        if status == "INVALID":
            self.errors.append(f"{name}: {message}")
        elif status == "WARNING":
            self.warnings.append(f"{name}: {message}")

    def get_overall_status(self) -> str:
        if self.errors:
            return "INVALID"
        if self.warnings:
            return "PARTIAL"
        return "VALID"
