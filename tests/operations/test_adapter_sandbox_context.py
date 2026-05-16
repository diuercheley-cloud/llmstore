import uuid
from app.services.operations.adapter_sandbox.sandbox_context import AdapterSandboxContext

def test_sandbox_context_can_perform():
    ctx = AdapterSandboxContext(
        client_id=uuid.uuid4(),
        manifest_id=uuid.uuid4(),
        sandbox_mode="simulation",
        allowed_capabilities=["restart", "cleanup"],
        denied_capabilities=["delete"]
    )
    assert ctx.can_perform("restart") is True
    assert ctx.can_perform("cleanup") is True
    assert ctx.can_perform("delete") is False
    assert ctx.can_perform("unknown") is False

def test_sandbox_context_denied_precedence():
    ctx = AdapterSandboxContext(
        client_id=uuid.uuid4(),
        manifest_id=uuid.uuid4(),
        sandbox_mode="simulation",
        allowed_capabilities=["restart"],
        denied_capabilities=["restart"]
    )
    assert ctx.can_perform("restart") is False
