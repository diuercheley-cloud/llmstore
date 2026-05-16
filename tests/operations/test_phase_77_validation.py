from scripts.validate_phase_77_federation_sync import validate


def test_phase_77_validation_script():
    failures = validate()
    assert failures == []
