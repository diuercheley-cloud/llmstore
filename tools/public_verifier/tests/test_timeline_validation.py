import hashlib

from tools.public_verifier.verifier_core import verify_timeline_chain


def test_verify_timeline_chain_valid():
    root = hashlib.sha256(b"root").hexdigest()
    prev = hashlib.sha256(b"prev").hexdigest()
    # combined = pair_hash(root, prev)
    combined = hashlib.sha256(bytes.fromhex(root) + bytes.fromhex(prev)).hexdigest()

    assert verify_timeline_chain(root, prev, combined) is True


def test_verify_timeline_chain_invalid():
    root = hashlib.sha256(b"root").hexdigest()
    prev = hashlib.sha256(b"prev").hexdigest()
    assert verify_timeline_chain(root, prev, "wrong_hash") is False
