import uuid
from unittest.mock import MagicMock

from app.models.commercial.commercial_policy_runtime import CommercialPolicyRuntimeBundle
from app.services.governance.policy_evaluator import PolicyEvaluator


def test_policy_evaluator_no_bundle(monkeypatch):
    mock_db = MagicMock()
    # Ensure query returns None
    mock_db.query().filter_by().first.return_value = None

    evaluator = PolicyEvaluator(mock_db)
    res = evaluator.evaluate("com.test", {}, {"tenant_id": str(uuid.uuid4())})

    assert res["allowed"] is True
    assert res["reason"] == "no_policy"


def test_policy_evaluator_enforce_allow(monkeypatch):
    mock_db = MagicMock()
    mock_bundle = CommercialPolicyRuntimeBundle(
        id=uuid.uuid4(),
        bundle_hash="hash",
        rego_hash="rego_hash",
        policy_namespace="com.test",
        immutable_hash="imm",
    )
    mock_db.query().filter_by().first.return_value = mock_bundle

    evaluator = PolicyEvaluator(mock_db)
    res = evaluator.evaluate("com.test", {"action": "read"}, {"tenant_id": str(uuid.uuid4())})

    assert res["allowed"] is True
    assert res["decision"] == "allow"
    assert len(res["violations"]) == 0


def test_policy_evaluator_enforce_deny(monkeypatch):
    mock_db = MagicMock()
    mock_bundle = CommercialPolicyRuntimeBundle(
        id=uuid.uuid4(),
        bundle_hash="hash",
        rego_hash="rego_hash",
        policy_namespace="com.test",
        immutable_hash="imm",
    )
    mock_db.query().filter_by().first.return_value = mock_bundle

    evaluator = PolicyEvaluator(mock_db)
    res = evaluator.evaluate("com.test", {"action": "restrict"}, {"tenant_id": str(uuid.uuid4())})

    assert res["allowed"] is False
    assert res["decision"] == "deny"
    assert len(res["violations"]) > 0


def test_policy_evaluator_advisory_mode(monkeypatch):
    mock_db = MagicMock()
    mock_bundle = CommercialPolicyRuntimeBundle(
        id=uuid.uuid4(),
        bundle_hash="hash",
        rego_hash="rego_hash",
        policy_namespace="com.test",
        immutable_hash="imm",
    )
    mock_db.query().filter_by().first.return_value = mock_bundle

    evaluator = PolicyEvaluator(mock_db)
    # the mode="advisory" will change a 'deny' to 'warn', allowing it
    res = evaluator.evaluate(
        "com.test", {"action": "restrict"}, {"tenant_id": str(uuid.uuid4())}, mode="advisory"
    )

    assert res["allowed"] is True
    assert res["decision"] == "warn"
    assert len(res["violations"]) > 0
