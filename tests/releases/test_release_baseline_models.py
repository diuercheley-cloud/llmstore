from control_plane.app.models.governance.release_baseline import (
    PlatformReleaseBaseline,
    ReleaseReceipt,
    ValidationSnapshot,
)


def test_platform_release_baseline_structure():
    baseline = PlatformReleaseBaseline(
        release_version="v1.9.0",
        baseline_scope=["Phase 69"],
        validation_snapshot_hash="snap_hash",
        release_hash="rel_hash",
        replay_safe=True,
        immutable_hash="imm_hash"
    )
    assert baseline.release_version == "v1.9.0"
    assert baseline.replay_safe is True

def test_validation_snapshot_structure():
    snapshot = ValidationSnapshot(
        validation_scope="smoke",
        validation_result={"all": "PASS"},
        validation_hash="val_hash",
        immutable_hash="imm_hash"
    )
    assert snapshot.validation_scope == "smoke"
    assert snapshot.validation_result["all"] == "PASS"

def test_release_receipt_structure():
    receipt = ReleaseReceipt(
        receipt_type="audit",
        payload_hash="pay_hash",
        immutable_hash="imm_hash",
        signature="[SIGNED]"
    )
    assert receipt.receipt_type == "audit"
    assert receipt.signature == "[SIGNED]"
