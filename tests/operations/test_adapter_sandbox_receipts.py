import uuid
from app.services.operations.adapter_sandbox.receipts import build_manifest_receipt, build_sandbox_run_receipt

def test_build_manifest_receipt():
    manifest = {
        "id": str(uuid.uuid4()),
        "client_id": str(uuid.uuid4()),
        "adapter_name": "test",
        "adapter_version": "1.0",
        "manifest_hash": "hash"
    }
    receipt = build_manifest_receipt(manifest)
    assert receipt["receipt_type"] == "adapter_manifest_registration"
    assert "immutable_hash" in receipt

def test_build_sandbox_run_receipt():
    class MockRun:
        id = uuid.uuid4()
        manifest_id = uuid.uuid4()
        client_id = uuid.uuid4()
        status = "simulated"
    
    run = MockRun()
    results = [{"status": "success"}]
    receipt = build_sandbox_run_receipt(run, results)
    assert receipt["receipt_type"] == "adapter_sandbox_run"
