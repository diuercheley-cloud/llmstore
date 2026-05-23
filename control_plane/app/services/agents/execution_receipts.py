# Owner: agent-platform
from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def sha256_hex(value: str | bytes) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def redact_confidential_payload(payload: Any, *, mode: str = "redacted") -> Any:
    if mode == "hash_only":
        return {"payload_hash": sha256_hex(canonical_json(payload))}
    if mode == "allow":
        return payload
    if isinstance(payload, dict):
        redacted: dict[str, Any] = {}
        for key, value in payload.items():
            key_lower = str(key).lower()
            if any(token in key_lower for token in ("secret", "token", "password", "credential", "payload", "content")):
                redacted[key] = "<redacted>"
            else:
                redacted[key] = redact_confidential_payload(value, mode=mode)
        return redacted
    if isinstance(payload, list):
        return [redact_confidential_payload(item, mode=mode) for item in payload]
    if isinstance(payload, str):
        if len(payload) > 12:
            return f"<redacted:{sha256_hex(payload)[:12]}>"
        return "<redacted>"
    return payload


def build_action_receipt(
    *,
    execution_id: str,
    tenant_id: str,
    action_index: int,
    tool_name: str,
    planned_input_hash: str,
    result_hash: str | None,
    policy_decision: str,
    runtime_snapshot_hash: str | None,
    previous_action_hash: str | None,
    execution_graph_hash: str | None,
    sandbox_context: dict[str, Any] | None,
) -> dict[str, Any]:
    body = {
        "execution_id": execution_id,
        "tenant_id": tenant_id,
        "action_index": action_index,
        "tool_name": tool_name,
        "planned_input_hash": planned_input_hash,
        "result_hash": result_hash,
        "policy_decision": policy_decision,
        "runtime_snapshot_hash": runtime_snapshot_hash,
        "previous_action_hash": previous_action_hash,
        "execution_graph_hash": execution_graph_hash,
        "sandbox_context": sandbox_context or {},
    }
    receipt_hash = sha256_hex(canonical_json(body))
    signature_algorithm = "ed25519_placeholder"
    detached_signature = f"placeholder_ed25519_{sha256_hex(receipt_hash + ':trusted-agent')[:48]}"
    immutable_hash = sha256_hex(
        canonical_json(
            {
                "receipt_hash": receipt_hash,
                "previous_action_hash": previous_action_hash,
                "detached_signature": detached_signature,
            }
        )
    )
    return {
        "body": body,
        "receipt_hash": receipt_hash,
        "detached_signature": detached_signature,
        "signature_algorithm": signature_algorithm,
        "immutable_hash": immutable_hash,
    }


def verify_action_receipt(receipt: dict[str, Any]) -> bool:
    expected = build_action_receipt(
        execution_id=receipt["body"]["execution_id"],
        tenant_id=receipt["body"]["tenant_id"],
        action_index=receipt["body"]["action_index"],
        tool_name=receipt["body"]["tool_name"],
        planned_input_hash=receipt["body"]["planned_input_hash"],
        result_hash=receipt["body"].get("result_hash"),
        policy_decision=receipt["body"]["policy_decision"],
        runtime_snapshot_hash=receipt["body"].get("runtime_snapshot_hash"),
        previous_action_hash=receipt["body"].get("previous_action_hash"),
        execution_graph_hash=receipt["body"].get("execution_graph_hash"),
        sandbox_context=receipt["body"].get("sandbox_context"),
    )
    return (
        expected["receipt_hash"] == receipt.get("receipt_hash")
        and expected["detached_signature"] == receipt.get("detached_signature")
        and expected["immutable_hash"] == receipt.get("immutable_hash")
    )
