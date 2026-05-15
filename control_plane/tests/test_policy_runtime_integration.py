import uuid
import pytest
from unittest.mock import MagicMock
from app.services.governance.policy_evaluator import PolicyEvaluator
from app.models.commercial_policy_runtime import CommercialPolicyRuntimeBundle

def test_policy_runtime_simulate_integration():
    mock_db = MagicMock()
    mock_bundle = CommercialPolicyRuntimeBundle(
        id=uuid.uuid4(),
        bundle_hash="hash",
        rego_hash="rego_hash",
        policy_namespace="com.test.sim",
        immutable_hash="imm"
    )
    mock_db.query().filter_by().first.return_value = mock_bundle
    
    evaluator = PolicyEvaluator(mock_db)
    res = evaluator.simulate("sim_1", "com.test.sim", {"action": "restrict"}, {"tenant_id": str(uuid.uuid4())})
    
    assert res["allowed"] is True # dry_run changes deny to warn, which is allowed
    assert res["decision"] == "warn"
    assert mock_db.add.called
    assert mock_db.commit.called
