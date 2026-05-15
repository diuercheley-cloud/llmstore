"""Merkle timeline service for verifiable AI execution proofs.

Provides canonical SHA256 Merkle tree construction, inclusion proofs,
timeline sealing, and chain validation.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


class MerkleError(Exception):
    """Base exception for Merkle operations."""


@dataclass(frozen=True)
class MerkleProofStep:
    """A single step in a Merkle inclusion proof."""

    sibling_hash: str
    is_right: bool


@dataclass(frozen=True)
class MerkleInclusionProof:
    """Proof that a leaf is included in a Merkle tree."""

    leaf_hash: str
    leaf_index: int
    steps: list[MerkleProofStep]
    root: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "leaf_hash": self.leaf_hash,
            "leaf_index": self.leaf_index,
            "root": self.root,
            "steps": [
                {"sibling_hash": step.sibling_hash, "is_right": step.is_right}
                for step in self.steps
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MerkleInclusionProof":
        return cls(
            leaf_hash=data["leaf_hash"],
            leaf_index=data["leaf_index"],
            root=data["root"],
            steps=[
                MerkleProofStep(step["sibling_hash"], step["is_right"])
                for step in data["steps"]
            ],
        )


# ---------------------------------------------------------------------------
# Core Merkle primitives
# ---------------------------------------------------------------------------

def _sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def canonical_leaf_hash(source_id: str, source_type: str, payload: dict[str, Any] | None = None) -> str:
    """Produce a deterministic SHA256 leaf hash for an item.

    The input is canonicalised as JSON (no extra whitespace, sorted keys)
    to ensure cross-platform determinism.
    """
    payload = payload or {}
    canonical: dict[str, Any] = {
        "source_id": source_id,
        "source_type": source_type,
        "payload": payload,
    }
    data = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _pair_hash(left: str, right: str) -> str:
    """Hash two child hex strings into a parent node."""
    combined = bytes.fromhex(left) + bytes.fromhex(right)
    return hashlib.sha256(combined).hexdigest()


def build_merkle_tree(leaves: list[str]) -> dict[int, list[str]]:
    """Build a full Merkle tree from a list of leaf hashes.

    Returns a dict mapping level -> list of node hashes at that level.
    Level 0 is the leaf level.
    """
    if not leaves:
        raise MerkleError("Cannot build Merkle tree from empty leaves")

    # Pad to next power of two if needed using the last leaf (self-propagating)
    padded = list(leaves)
    n = len(padded)
    if n & (n - 1) != 0:  # not power of two
        next_pow = 1 << (n - 1).bit_length()
        padded.extend([padded[-1]] * (next_pow - n))

    tree: dict[int, list[str]] = {0: padded}
    level = 0
    while len(tree[level]) > 1:
        current = tree[level]
        parents = []
        for i in range(0, len(current), 2):
            left = current[i]
            right = current[i + 1]
            parents.append(_pair_hash(left, right))
        tree[level + 1] = parents
        level += 1
    return tree


def calculate_merkle_root(leaves: list[str]) -> str:
    """Return the Merkle root for a list of leaf hashes."""
    tree = build_merkle_tree(leaves)
    return tree[max(tree.keys())][0]


def generate_inclusion_proof(leaf_index: int, leaves: list[str]) -> MerkleInclusionProof:
    """Generate an inclusion proof for the leaf at *leaf_index*.

    The proof consists of the sibling hash at each level needed to
    reconstruct the root.
    """
    if not leaves or leaf_index < 0 or leaf_index >= len(leaves):
        raise MerkleError("Invalid leaf index")

    tree = build_merkle_tree(leaves)
    steps: list[MerkleProofStep] = []
    idx = leaf_index

    for level in range(max(tree.keys())):
        level_nodes = tree[level]
        sibling = idx ^ 1
        if sibling >= len(level_nodes):
            raise MerkleError("Tree structure mismatch during proof generation")
        is_right = (idx % 2) == 1
        steps.append(MerkleProofStep(level_nodes[sibling], is_right))
        idx //= 2

    return MerkleInclusionProof(
        leaf_hash=leaves[leaf_index],
        leaf_index=leaf_index,
        steps=steps,
        root=tree[max(tree.keys())][0],
    )


def verify_inclusion_proof(proof: MerkleInclusionProof) -> bool:
    """Verify an inclusion proof against its claimed root.

    Recomputes the path from leaf to root using the sibling hashes.
    """
    current = proof.leaf_hash
    for step in proof.steps:
        if step.is_right:
            current = _pair_hash(step.sibling_hash, current)
        else:
            current = _pair_hash(current, step.sibling_hash)
    return current == proof.root


# ---------------------------------------------------------------------------
# Timeline sealing / chain validation
# ---------------------------------------------------------------------------

def seal_timeline(
    leaves: list[str],
    previous_root: str | None = None,
) -> str:
    """Seal a timeline by computing its Merkle root.

    Optionally incorporate the previous timeline root into the final hash
    to form a chain.
    """
    root = calculate_merkle_root(leaves)
    if previous_root:
        # Chain the previous root into the current root
        root = _pair_hash(root, previous_root)
    return root


def validate_timeline_chain(
    timeline_root: str,
    previous_root: str | None,
    expected_combined_root: str | None,
) -> bool:
    """Validate that a timeline root correctly chains to a previous root.

    If *expected_combined_root* is provided, verify that
    pair_hash(timeline_root, previous_root) == expected_combined_root.
    """
    if previous_root is None or expected_combined_root is None:
        return True
    combined = _pair_hash(timeline_root, previous_root)
    return combined == expected_combined_root


def summarize_timelines(timelines: list[dict[str, Any]]) -> dict[str, Any]:
    """Produce a condensed summary of multiple timelines for public verification."""
    total_leaves = sum(t.get("leaf_count", 0) for t in timelines)
    sealed = sum(1 for t in timelines if t.get("status") == "sealed")
    verified = sum(1 for t in timelines if t.get("status") == "verified")
    invalid = sum(1 for t in timelines if t.get("status") == "invalid")
    chain_valid = True
    for i in range(1, len(timelines)):
        prev_root = timelines[i - 1].get("merkle_root")
        curr_prev = timelines[i].get("previous_timeline_root")
        if curr_prev != prev_root:
            chain_valid = False
            break

    return {
        "total_timelines": len(timelines),
        "total_leaves": total_leaves,
        "sealed_count": sealed,
        "verified_count": verified,
        "invalid_count": invalid,
        "chain_valid": chain_valid,
        "latest_root": timelines[-1].get("merkle_root") if timelines else None,
    }
