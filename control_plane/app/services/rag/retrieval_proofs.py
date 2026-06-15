from __future__ import annotations

import hashlib
import json
import uuid
from datetime import timedelta
from typing import Any

from app.core.time import utc_now
from app.models.commercial.commercial_merkle_timelines import (
    CommercialMerkleLeaf,
    CommercialMerkleTimeline,
)
from app.models.commercial.commercial_rag_vault import (
    CommercialRAGRetrievalAudit,
    CommercialRAGVault,
)
from app.models.commercial.commercial_retrieval_proofs import (
    CommercialContextLineage,
    CommercialRetrievalMerkleLeaf,
    CommercialRetrievalProof,
    CommercialRetrievalReplayRecord,
)
from app.services.inference.merkle_timelines import (
    MerkleInclusionProof,
    calculate_merkle_root,
    canonical_leaf_hash,
    generate_inclusion_proof,
    seal_timeline,
    verify_inclusion_proof,
)
from app.services.inference.witness_federation import evaluate_witness_quorum
from app.services.routing.commercial_report_export import sanitize_report_payload
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession


def _canonical(payload: Any) -> str:
    return json.dumps(
        sanitize_report_payload(payload),
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
        default=str,
    )


def _sha256(payload: Any) -> str:
    if isinstance(payload, bytes):
        data = payload
    else:
        data = _canonical(payload).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _token_overlap(a: list[str], b: list[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    sa = set(a)
    sb = set(b)
    return round(len(sa & sb) / max(len(sa | sb), 1), 4)


async def generate_retrieval_proof(
    session: AsyncSession,
    *,
    vault: CommercialRAGVault,
    audit: CommercialRAGRetrievalAudit,
    sources: list[Any],
    retrieval_metadata: dict[str, Any],
    model_id: str | None,
) -> CommercialRetrievalProof:
    policy_payload = {
        "policy_result": retrieval_metadata.get("policy_result", audit.policy_result),
        "violations": retrieval_metadata.get("violations", []),
        "governed": retrieval_metadata.get("governed", False),
        "max_context_chunks": retrieval_metadata.get("max_context_chunks"),
    }
    policy_hash = _sha256(policy_payload)

    source_items = [
        {
            "document_id": str(src.document_id),
            "filename": src.filename,
            "page": src.page,
            "chunk_index": src.chunk_index,
            "text_hash": _sha256(src.text),
            "score": round(float(src.score), 6),
        }
        for src in sources
    ]
    retrieval_sent_payload = {
        "retrieval_audit_id": str(audit.id),
        "request_hash": audit.request_hash,
        "retrieval_hash": audit.retrieval_hash,
        "model_id": model_id,
        "sources": source_items,
    }
    retrieval_sent_hash = _sha256(retrieval_sent_payload)

    previous_timeline = (
        await session.execute(
            select(CommercialMerkleTimeline)
            .where(CommercialMerkleTimeline.timeline_type == "retrieval_proofs")
            .order_by(desc(CommercialMerkleTimeline.created_at))
            .limit(1)
        )
    ).scalar_one_or_none()
    previous_root = previous_timeline.merkle_root if previous_timeline else None

    proof = CommercialRetrievalProof(
        retrieval_audit_id=audit.id,
        vault_id=vault.id,
        timeline_id=None,
        proof_hash="pending",
        policy_hash=policy_hash,
        lineage_root_hash="pending",
        retrieval_sent_hash=retrieval_sent_hash,
        merkle_root="pending",
        proof_json={},
        verification_status="pending",
    )
    session.add(proof)
    await session.flush()

    lineage_root_id = await _persist_lineage(
        session, proof=proof, policy_payload=policy_payload, source_items=source_items
    )
    lineage_rows = (
        (
            await session.execute(
                select(CommercialContextLineage)
                .where(CommercialContextLineage.retrieval_proof_id == proof.id)
                .order_by(
                    CommercialContextLineage.depth.asc(), CommercialContextLineage.created_at.asc()
                )
            )
        )
        .scalars()
        .all()
    )
    lineage_root_hash = _sha256(
        {
            "root": str(lineage_root_id) if lineage_root_id else None,
            "nodes": [row.node_hash for row in lineage_rows],
        }
    )

    leaf_specs = [
        ("policy", f"policy:{audit.id}", policy_hash, policy_payload),
        (
            "retrieval_sent",
            f"retrieval:{audit.id}",
            retrieval_sent_hash,
            {"retrieved_chunk_count": audit.retrieved_chunk_count},
        ),
    ]
    for item in source_items:
        leaf_specs.append(
            (
                "chunk",
                f"{item['document_id']}:{item['chunk_index']}",
                canonical_leaf_hash(
                    source_id=f"{item['document_id']}:{item['chunk_index']}",
                    source_type="retrieved_chunk",
                    payload={
                        "text_hash": item["text_hash"],
                        "page": item["page"],
                        "score": item["score"],
                    },
                ),
                {"document_id": item["document_id"], "page": item["page"]},
            )
        )

    leaf_hashes: list[str] = []
    for index, (source_type, source_id, leaf_hash, metadata) in enumerate(leaf_specs):
        leaf_hashes.append(leaf_hash)
        session.add(
            CommercialRetrievalMerkleLeaf(
                retrieval_proof_id=proof.id,
                source_type=source_type,
                source_id=source_id,
                leaf_hash=leaf_hash,
                leaf_index=index,
                metadata_json=sanitize_report_payload(metadata),
            )
        )

    raw_root = calculate_merkle_root(leaf_hashes)
    merkle_root = seal_timeline(leaf_hashes, previous_root)
    inclusion = generate_inclusion_proof(1, leaf_hashes)
    inclusion_dict = inclusion.to_dict()
    inclusion_dict["root"] = raw_root

    timeline = CommercialMerkleTimeline(
        timeline_type="retrieval_proofs",
        period_start=audit.created_at,
        period_end=audit.created_at + timedelta(seconds=1),
        leaf_count=len(leaf_hashes),
        merkle_root=merkle_root,
        previous_timeline_root=previous_root,
        timeline_hash=merkle_root,
        status="sealed",
        sealed_at=utc_now(),
    )
    session.add(timeline)
    await session.flush()
    proof.timeline_id = timeline.id

    for index, (_, source_id, leaf_hash, metadata) in enumerate(leaf_specs):
        session.add(
            CommercialMerkleLeaf(
                timeline_id=timeline.id,
                source_type="retrieval_proof_leaf",
                source_id=source_id,
                leaf_hash=leaf_hash,
                leaf_index=index,
                metadata_json=sanitize_report_payload(metadata),
            )
        )

    quorum = await evaluate_witness_quorum(session, timeline.id)
    witness_summary = {
        "quorum_status": "VALID"
        if quorum.get("quorum_status") == "met"
        else ("PARTIAL" if quorum.get("signatures_found", 0) > 0 else "INVALID"),
        "required_signatures": quorum.get("signatures_required", 0),
        "signatures_found": quorum.get("signatures_found", 0),
        "external_witness_present": quorum.get("external_witness_present", False),
        "signatures": [
            {
                "witness_name": item.get("witness_id", "unknown"),
                "witness_type": "external" if quorum.get("external_witness_present") else "local",
                "signature": item.get("signature", ""),
                "signature_algorithm": "ed25519",
                "signed_at": item.get("signed_at"),
            }
            for item in quorum.get("signatures", [])
        ],
    }
    proof_json = {
        "proof_type": "retrieval",
        "retrieval_audit_id": str(audit.id),
        "timeline_id": str(timeline.id),
        "timeline_root": merkle_root,
        "raw_merkle_root": raw_root,
        "previous_timeline_root": previous_root,
        "merkle_inclusion_proof": inclusion_dict,
        "policy_hash": policy_hash,
        "lineage_root_hash": lineage_root_hash,
        "retrieval_sent_hash": retrieval_sent_hash,
        "retrieval_hash": audit.retrieval_hash,
        "request_hash": audit.request_hash,
        "retrieved_chunk_count": audit.retrieved_chunk_count,
        "model_id": model_id,
        "chunk_participants": [
            {
                "document_id": item["document_id"],
                "chunk_index": item["chunk_index"],
                "page": item["page"],
                "text_hash": item["text_hash"],
            }
            for item in source_items
        ],
        "document_participants": sorted({item["document_id"] for item in source_items}),
        "lineage_chain": [
            {
                "node_type": row.node_type,
                "node_hash": row.node_hash,
                "parent_lineage_id": str(row.parent_lineage_id) if row.parent_lineage_id else None,
                "source_id": row.source_id,
                "depth": row.depth,
            }
            for row in lineage_rows
        ],
        "receipt_link": {
            "retrieval_audit_immutable_hash": audit.immutable_hash,
        },
        "confidential_runtime_summary": {
            "required": "confidential_runtime_required"
            in (retrieval_metadata.get("violations") or []),
            "plaintext_retained": False,
        },
        "witness_quorum_summary": sanitize_report_payload(witness_summary),
        "transparency_gossip_summary": {
            "timeline_type": "retrieval_proofs",
            "eligible_for_checkpoint": True,
        },
        "created_at": utc_now().isoformat(),
    }
    proof.proof_json = sanitize_report_payload(proof_json)
    proof.lineage_root_hash = lineage_root_hash
    proof.merkle_root = merkle_root
    proof.proof_hash = _sha256(proof.proof_json)
    proof.export_hash = _sha256({"proof_hash": proof.proof_hash, "merkle_root": merkle_root})
    await session.flush()
    return proof


async def _persist_lineage(
    session: AsyncSession,
    *,
    proof: CommercialRetrievalProof,
    policy_payload: dict[str, Any],
    source_items: list[dict[str, Any]],
) -> uuid.UUID | None:
    policy_node = CommercialContextLineage(
        retrieval_proof_id=proof.id,
        parent_lineage_id=None,
        node_type="policy",
        node_hash=_sha256(policy_payload),
        source_id=str(proof.retrieval_audit_id),
        source_label="retrieval_policy",
        depth=0,
        metadata_json=sanitize_report_payload(policy_payload),
    )
    session.add(policy_node)
    await session.flush()

    document_nodes: dict[str, uuid.UUID] = {}
    for item in source_items:
        if item["document_id"] not in document_nodes:
            doc_node = CommercialContextLineage(
                retrieval_proof_id=proof.id,
                parent_lineage_id=policy_node.id,
                node_type="document",
                node_hash=_sha256({"document_id": item["document_id"]}),
                source_id=item["document_id"],
                source_label=item["filename"],
                depth=1,
                metadata_json={"document_id": item["document_id"]},
            )
            session.add(doc_node)
            await session.flush()
            document_nodes[item["document_id"]] = doc_node.id

        chunk_node = CommercialContextLineage(
            retrieval_proof_id=proof.id,
            parent_lineage_id=document_nodes[item["document_id"]],
            node_type="chunk",
            node_hash=_sha256(item),
            source_id=f"{item['document_id']}:{item['chunk_index']}",
            source_label=f"chunk:{item['chunk_index']}",
            depth=2,
            metadata_json=sanitize_report_payload(item),
        )
        session.add(chunk_node)
        await session.flush()

    retrieval_node = CommercialContextLineage(
        retrieval_proof_id=proof.id,
        parent_lineage_id=policy_node.id,
        node_type="retrieval",
        node_hash=proof.retrieval_sent_hash,
        source_id=str(proof.retrieval_audit_id),
        source_label="retrieval_sent",
        depth=3,
        metadata_json={"retrieval_sent_hash": proof.retrieval_sent_hash},
    )
    session.add(retrieval_node)
    await session.flush()
    return policy_node.id


async def verify_retrieval_proof(
    session: AsyncSession, proof: CommercialRetrievalProof
) -> dict[str, Any]:
    inclusion = MerkleInclusionProof.from_dict(proof.proof_json.get("merkle_inclusion_proof", {}))
    merkle_valid = verify_inclusion_proof(inclusion)
    lineage_valid = await verify_lineage_consistency(session, proof)
    recomputed_hash = _sha256({k: v for k, v in proof.proof_json.items() if k != "proof_hash"})
    proof_hash_valid = recomputed_hash == proof.proof_hash
    timeline_valid = proof.proof_json.get("timeline_root") == proof.merkle_root
    proof.verification_status = (
        "valid"
        if all([merkle_valid, lineage_valid, proof_hash_valid, timeline_valid])
        else "invalid"
    )
    proof.verified_at = utc_now()
    await session.flush()
    return {
        "valid": proof.verification_status == "valid",
        "merkle_valid": merkle_valid,
        "lineage_valid": lineage_valid,
        "proof_hash_valid": proof_hash_valid,
        "timeline_valid": timeline_valid,
    }


async def verify_lineage_consistency(
    session: AsyncSession, proof: CommercialRetrievalProof
) -> bool:
    rows = (
        (
            await session.execute(
                select(CommercialContextLineage)
                .where(CommercialContextLineage.retrieval_proof_id == proof.id)
                .order_by(
                    CommercialContextLineage.depth.asc(), CommercialContextLineage.created_at.asc()
                )
            )
        )
        .scalars()
        .all()
    )
    if not rows:
        return False
    lineage_root_hash = _sha256({"root": str(rows[0].id), "nodes": [row.node_hash for row in rows]})
    return lineage_root_hash == proof.lineage_root_hash


async def replay_retrieval_proof(
    session: AsyncSession,
    *,
    proof: CommercialRetrievalProof,
    replay_sources: list[dict[str, Any]],
) -> CommercialRetrievalReplayRecord:
    replay_payload = {
        "sources": [
            {
                "document_id": str(item["document_id"]),
                "chunk_index": int(item["chunk_index"]),
                "text_hash": item["text_hash"],
            }
            for item in replay_sources
        ]
    }
    replay_hash = _sha256(replay_payload)
    original = proof.proof_json.get("chunk_participants", [])
    original_tokens = [
        f"{item['document_id']}:{item['chunk_index']}:{item['text_hash']}" for item in original
    ]
    replay_tokens = [
        f"{item['document_id']}:{item['chunk_index']}:{item['text_hash']}"
        for item in replay_payload["sources"]
    ]
    drift_score = round(1.0 - _token_overlap(original_tokens, replay_tokens), 4)
    drift_status = (
        "stable" if drift_score == 0.0 else ("minor_drift" if drift_score < 0.5 else "major_drift")
    )
    replay_status = "matched" if drift_score == 0.0 else "drift_detected"
    record = CommercialRetrievalReplayRecord(
        retrieval_proof_id=proof.id,
        replay_hash=replay_hash,
        replay_status=replay_status,
        drift_status=drift_status,
        drift_score=drift_score,
        summary=f"retrieval_replay:{replay_status}",
        metadata_json=sanitize_report_payload(
            {
                "original_count": len(original_tokens),
                "replay_count": len(replay_tokens),
                "proof_hash": proof.proof_hash,
            }
        ),
        replayed_at=utc_now(),
        verified_at=utc_now(),
    )
    session.add(record)
    await session.flush()
    return record


async def export_retrieval_proof(
    session: AsyncSession, proof: CommercialRetrievalProof
) -> dict[str, Any]:
    replays = (
        (
            await session.execute(
                select(CommercialRetrievalReplayRecord)
                .where(CommercialRetrievalReplayRecord.retrieval_proof_id == proof.id)
                .order_by(CommercialRetrievalReplayRecord.created_at.desc())
                .limit(20)
            )
        )
        .scalars()
        .all()
    )
    payload = dict(proof.proof_json)
    payload["proof_hash"] = proof.proof_hash
    payload["verification_status"] = proof.verification_status
    payload["replay_records"] = [
        {
            "replay_hash": item.replay_hash,
            "replay_status": item.replay_status,
            "drift_status": item.drift_status,
            "drift_score": item.drift_score,
            "verified_at": item.verified_at.isoformat() if item.verified_at else None,
        }
        for item in replays
    ]
    return sanitize_report_payload(payload)
