import uuid

from app.services.operations.adapter_sandbox.sandbox_context import AdapterSandboxContext
from app.services.operations.adapter_sandbox.simulation_runner import AdapterSandboxSimulationRunner


def test_simulation_runner_simulate_step():
    runner = AdapterSandboxSimulationRunner()
    ctx = AdapterSandboxContext(
        client_id=uuid.uuid4(),
        manifest_id=uuid.uuid4(),
        sandbox_mode="simulation",
        allowed_capabilities=["restart"],
        approval_verified=True,
        gates_verified=True,
    )
    step = {"action_type": "restart", "target_domain": "worker"}
    res = runner.simulate_step(ctx, step)
    assert res["result_status"] == "success"
    assert res["simulated_output_json"]["simulated_action"] == "restart"


def test_simulation_runner_denied_step():
    runner = AdapterSandboxSimulationRunner()
    ctx = AdapterSandboxContext(
        client_id=uuid.uuid4(),
        manifest_id=uuid.uuid4(),
        sandbox_mode="simulation",
        allowed_capabilities=[],
        approval_verified=True,
        gates_verified=True,
    )
    step = {"action_type": "restart", "target_domain": "worker"}
    res = runner.simulate_step(ctx, step)
    assert res["result_status"] == "denied"
