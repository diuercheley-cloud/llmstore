from scripts.validate_phase_78_compatibility_contracts import validate


def test_phase_78_validation_script():
    failures = validate()
    assert failures == []
