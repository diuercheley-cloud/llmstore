import pytest
from app.services.operations.correlation.receipts import (
    build_correlation_receipt,
    build_trust_link_receipt,
    build_graph_summary_receipt
)

def test_build_correlation_receipt():
    correlation = {
        "immutable_hash": "corr_hash_123",
        "correlation_type": "cross_domain",
        "correlation_key": "billing_runtime_repro",
        "involved_domains": ["billing", "runtime"]
    }
    receipt = build_correlation_receipt(correlation)
    
    assert receipt["receipt_type"] == "operational_correlation"
    assert receipt["immutable_hash"] == "corr_hash_123"
    assert "payload_hash" in receipt
    assert receipt["advisory_only"] is True
    assert receipt["signature_placeholder"].startswith("sig_placeholder_")
    assert "generated_at" in receipt

def test_build_trust_link_receipt():
    link = {
        "immutable_hash": "link_hash_456",
        "source_node": "auth",
        "target_node": "inference",
        "trust_relation": "depends_on"
    }
    receipt = build_trust_link_receipt(link)
    
    assert receipt["receipt_type"] == "operational_trust_link"
    assert receipt["immutable_hash"] == "link_hash_456"
    assert receipt["advisory_only"] is True

def test_build_graph_summary_receipt():
    summary = {
        "node_count": 5,
        "edge_count": 10,
        "aggregate_confidence": 0.85,
        "nodes": ["a", "b", "c"],
        "edges": [{"from": "a", "to": "b"}]
    }
    receipt = build_graph_summary_receipt(summary)
    
    assert receipt["receipt_type"] == "trust_graph_summary"
    assert receipt["advisory_only"] is True
    assert "payload_hash" in receipt
