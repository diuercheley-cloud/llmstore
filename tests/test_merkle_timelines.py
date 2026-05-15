"""Tests for Merkle timelines."""

from __future__ import annotations

import hashlib

import pytest

from app.services.inference.merkle_timelines import (
    MerkleError,
    calculate_merkle_root,
    canonical_leaf_hash,
    generate_inclusion_proof,
    seal_timeline,
    summarize_timelines,
    validate_timeline_chain,
    verify_inclusion_proof,
)


class TestMerkleCore:
    def test_canonical_leaf_hash_deterministic(self):
        h1 = canonical_leaf_hash("id-1", "receipt", {"key": "value"})
        h2 = canonical_leaf_hash("id-1", "receipt", {"key": "value"})
        assert h1 == h2
        assert len(h1) == 64

    def test_canonical_leaf_hash_different_inputs(self):
        h1 = canonical_leaf_hash("id-1", "receipt", {"key": "value"})
        h2 = canonical_leaf_hash("id-2", "receipt", {"key": "value"})
        assert h1 != h2

    def test_merkle_root_deterministic(self):
        leaves = [
            canonical_leaf_hash(f"id-{i}", "receipt", {"idx": i})
            for i in range(4)
        ]
        root1 = calculate_merkle_root(leaves)
        root2 = calculate_merkle_root(leaves)
        assert root1 == root2
        assert len(root1) == 64

    def test_merkle_root_empty_raises(self):
        with pytest.raises(MerkleError):
            calculate_merkle_root([])

    def test_inclusion_proof_valid(self):
        leaves = [
            canonical_leaf_hash(f"id-{i}", "receipt", {"idx": i})
            for i in range(8)
        ]
        proof = generate_inclusion_proof(3, leaves)
        assert proof.leaf_index == 3
        assert proof.root == calculate_merkle_root(leaves)
        assert verify_inclusion_proof(proof) is True

    def test_inclusion_proof_invalid_after_tamper(self):
        leaves = [
            canonical_leaf_hash(f"id-{i}", "receipt", {"idx": i})
            for i in range(8)
        ]
        proof = generate_inclusion_proof(3, leaves)
        # Tamper with the leaf hash
        tampered_proof = type(proof)(
            leaf_hash=canonical_leaf_hash("tampered", "receipt", {}),
            leaf_index=proof.leaf_index,
            steps=proof.steps,
            root=proof.root,
        )
        assert verify_inclusion_proof(tampered_proof) is False

    def test_inclusion_proof_invalid_root(self):
        leaves = [
            canonical_leaf_hash(f"id-{i}", "receipt", {"idx": i})
            for i in range(8)
        ]
        proof = generate_inclusion_proof(3, leaves)
        tampered_root = hashlib.sha256(b"wrong-root").hexdigest()
        tampered_proof = type(proof)(
            leaf_hash=proof.leaf_hash,
            leaf_index=proof.leaf_index,
            steps=proof.steps,
            root=tampered_root,
        )
        assert verify_inclusion_proof(tampered_proof) is False

    def test_seal_timeline_basic(self):
        leaves = [
            canonical_leaf_hash(f"id-{i}", "receipt", {"idx": i})
            for i in range(4)
        ]
        root = seal_timeline(leaves)
        assert len(root) == 64
        assert root == calculate_merkle_root(leaves)

    def test_seal_timeline_with_previous_root(self):
        leaves = [
            canonical_leaf_hash(f"id-{i}", "receipt", {"idx": i})
            for i in range(4)
        ]
        previous = hashlib.sha256(b"previous").hexdigest()
        root = seal_timeline(leaves, previous)
        assert len(root) == 64
        assert root != calculate_merkle_root(leaves)

    def test_validate_timeline_chain_no_previous(self):
        leaves = [
            canonical_leaf_hash(f"id-{i}", "receipt", {"idx": i})
            for i in range(4)
        ]
        root = seal_timeline(leaves)
        assert validate_timeline_chain(root, None, None) is True

    def test_validate_timeline_chain_valid(self):
        leaves = [
            canonical_leaf_hash(f"id-{i}", "receipt", {"idx": i})
            for i in range(4)
        ]
        previous = hashlib.sha256(b"previous").hexdigest()
        unchained_root = calculate_merkle_root(leaves)
        chained_root = seal_timeline(leaves, previous)
        assert validate_timeline_chain(unchained_root, previous, chained_root) is True

    def test_summarize_timelines(self):
        timelines = [
            {
                "leaf_count": 10,
                "status": "sealed",
                "merkle_root": "root-1",
            },
            {
                "leaf_count": 20,
                "status": "verified",
                "merkle_root": "root-2",
                "previous_timeline_root": "root-1",
            },
            {
                "leaf_count": 5,
                "status": "invalid",
                "merkle_root": "root-3",
                "previous_timeline_root": "root-2",
            },
        ]
        summary = summarize_timelines(timelines)
        assert summary["total_timelines"] == 3
        assert summary["total_leaves"] == 35
        assert summary["sealed_count"] == 1
        assert summary["verified_count"] == 1
        assert summary["invalid_count"] == 1
        assert summary["chain_valid"] is True
        assert summary["latest_root"] == "root-3"

    def test_summarize_timelines_tampered_chain(self):
        timelines = [
            {
                "leaf_count": 10,
                "status": "sealed",
                "merkle_root": "root-a",
            },
            {
                "leaf_count": 20,
                "status": "sealed",
                "merkle_root": "root-b",
                "previous_timeline_root": "root-wrong",
            },
        ]
        summary = summarize_timelines(timelines)
        assert summary["chain_valid"] is False


class TestMerkleProofEdgeCases:
    def test_inclusion_proof_single_leaf(self):
        leaves = [canonical_leaf_hash("only", "receipt", {})]
        proof = generate_inclusion_proof(0, leaves)
        assert verify_inclusion_proof(proof) is True
        assert len(proof.steps) == 0

    def test_inclusion_proof_not_power_of_two(self):
        leaves = [canonical_leaf_hash(f"id-{i}", "receipt", {"idx": i}) for i in range(5)]
        proof = generate_inclusion_proof(2, leaves)
        assert verify_inclusion_proof(proof) is True

    def test_inclusion_proof_out_of_range(self):
        leaves = [canonical_leaf_hash(f"id-{i}", "receipt", {"idx": i}) for i in range(4)]
        with pytest.raises(MerkleError):
            generate_inclusion_proof(10, leaves)
