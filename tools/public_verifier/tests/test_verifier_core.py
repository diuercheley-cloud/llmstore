
import json

from tools.public_verifier.verifier_core import (
    Verifier,
    _pair_hash,
    _sha256_hex,
    verify_merkle_path,
)


def test_merkle_path_validation():
    # Simple tree: [L1, L2] -> Root
    l1 = _sha256_hex("leaf1")
    l2 = _sha256_hex("leaf2")
    root = _pair_hash(l1, l2)
    
    proof_data = {
        "leaf_hash": l1,
        "leaf_index": 0,
        "steps": [{"sibling_hash": l2, "is_right": False}],
        "root": root
    }
    
    from tools.public_verifier.verifier_models import MerkleInclusionProof
    proof = MerkleInclusionProof(**proof_data)
    assert verify_merkle_path(proof) is True

def test_verifier_run_all_checks():
    # Create a dummy valid proof
    l1 = _sha256_hex("leaf1")
    l2 = _sha256_hex("leaf2")
    root = _pair_hash(l1, l2)
    
    proof_json = {
        "proof_type": "execution",
        "proof_hash": "", # will be set below
        "verification_status": "pending",
        "timeline_root": root,
        "previous_timeline_root": "prev_root",
        "merkle_inclusion_proof": {
            "leaf_hash": l1,
            "leaf_index": 0,
            "steps": [{"sibling_hash": l2, "is_right": False}],
            "root": root
        },
        "replay_verification_summary": {
            "chain_valid": True,
            "signature_valid": True
        }
    }
    
    # Calculate correct proof_hash (excluding proof_hash and verification_status)
    to_hash = proof_json.copy()
    to_hash.pop("proof_hash", None)
    to_hash.pop("verification_status", None)
    canonical = json.dumps(to_hash, sort_keys=True, separators=(",", ":"))
    proof_json["proof_hash"] = _sha256_hex(canonical)
    
    v = Verifier(proof_json)
    v.run_all_checks()
    
    assert v.get_overall_status() == "VALID"
    assert len(v.errors) == 0

def test_verifier_detects_tamper():
    l1 = _sha256_hex("leaf1")
    l2 = _sha256_hex("leaf2")
    root = _pair_hash(l1, l2)
    
    proof_json = {
        "proof_type": "execution",
        "proof_hash": "wrong_hash",
        "verification_status": "pending",
        "timeline_root": root,
        "merkle_inclusion_proof": {
            "leaf_hash": l1,
            "leaf_index": 0,
            "steps": [{"sibling_hash": l2, "is_right": False}],
            "root": root
        }
    }
    
    v = Verifier(proof_json)
    v.run_all_checks()
    
    assert v.get_overall_status() == "INVALID"
    assert any("Proof Hash" in e for e in v.errors)
