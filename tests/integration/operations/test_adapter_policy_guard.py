import uuid

from app.services.operations.adapter_sandbox.policy_guard import AdapterSandboxPolicyGuard
from app.services.operations.adapter_sandbox.sandbox_context import AdapterSandboxContext


def test_policy_guard_inspect_manifest_network():
    guard = AdapterSandboxPolicyGuard()
    manifest = {"network_access_allowed": True}
    violations = guard.inspect_manifest(manifest)
    assert len(violations) == 1
    assert violations[0]["violation_type"] == "network_policy"

def test_policy_guard_inspect_execution_unsafe():
    guard = AdapterSandboxPolicyGuard()
    ctx = AdapterSandboxContext(
        client_id=uuid.uuid4(),
        manifest_id=uuid.uuid4(),
        sandbox_mode="simulation",
        allowed_capabilities=["shell"]
    )
    violations = guard.inspect_execution_request(ctx, "shell")
    assert any(v["violation_type"] == "unsafe_action" for v in violations)

def test_policy_guard_block_logic():
    guard = AdapterSandboxPolicyGuard()
    violations = [{"blocked": True}, {"blocked": False}]
    assert guard.block_if_violation(violations) is True
    assert guard.block_if_violation([{"blocked": False}]) is False
