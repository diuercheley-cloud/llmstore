import hashlib
import json
from datetime import datetime
from typing import Any, Dict

from app.core.time import utc_now
from app.utils.crypto_signer import sign_payload

def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)

def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()

def _build_receipt(receipt_type: str, immutable_hash: str, payload: Any, version: str = "v1") -> Dict[str, Any]:
    payload_json = _canonical_json(payload)
    payload_hash = _sha256(payload_json)
    
    # Signature
    receipt_hash = _sha256(f"{receipt_type}:{immutable_hash}:{payload_hash}:{version}")
    signature = sign_payload(f"{receipt_hash[:32]}")
    
    return {
        "receipt_type": receipt_type,
        "immutable_hash": immutable_hash,
        "payload_hash": payload_hash,
        "deterministic_version": version,
        "advisory_only": True,
        "signature": signature,
        "generated_at": utc_now().isoformat()
    }

def build_correlation_receipt(correlation: Dict[str, Any]) -> Dict[str, Any]:
    return _build_receipt(
        receipt_type="operational_correlation",
        immutable_hash=correlation.get("immutable_hash", "unknown"),
        payload={
            "correlation_type": correlation.get("correlation_type"),
            "correlation_key": correlation.get("correlation_key"),
            "involved_domains": correlation.get("involved_domains")
        }
    )

def build_trust_link_receipt(link: Dict[str, Any]) -> Dict[str, Any]:
    return _build_receipt(
        receipt_type="operational_trust_link",
        immutable_hash=link.get("immutable_hash", "unknown"),
        payload={
            "source_node": link.get("source_node"),
            "target_node": link.get("target_node"),
            "trust_relation": link.get("trust_relation")
        }
    )

def build_graph_summary_receipt(summary: Dict[str, Any]) -> Dict[str, Any]:
    return _build_receipt(
        receipt_type="trust_graph_summary",
        immutable_hash=_sha256(_canonical_json(summary.get("nodes", [])) + _sha256(_canonical_json(summary.get("edges", [])))),
        payload={
            "node_count": summary.get("node_count"),
            "edge_count": summary.get("edge_count"),
            "aggregate_confidence": summary.get("aggregate_confidence")
        }
    )
