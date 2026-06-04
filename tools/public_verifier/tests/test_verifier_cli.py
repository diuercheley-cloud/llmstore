import json

from tools.public_verifier.verifier_cli import verify_file


def test_verify_file_non_existent():
    assert verify_file("non_existent.json") is False

def test_verify_file_invalid_json(tmp_path):
    d = tmp_path / "invalid.json"
    d.write_text("not json")
    assert verify_file(str(d)) is False

def test_verify_file_valid_mock(tmp_path):
    # This requires a properly hashed proof, which we test in core.
    # Here we just check the CLI plumbing works with a minimal valid-looking structure.
    # However, since run_all_checks will fail on hash mismatch, we'll just check it returns False
    # and doesn't crash.
    d = tmp_path / "proof.json"
    d.write_text(json.dumps({"proof_type": "test", "proof_hash": "abc", "verification_status": "pending", "timeline_root": "root", "merkle_inclusion_proof": {"leaf_hash": "l", "leaf_index": 0, "steps": [], "root": "root"}}))
    assert verify_file(str(d)) is False # Expected to be invalid due to hash mismatch
