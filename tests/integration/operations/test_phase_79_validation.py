from scripts.validate_phase_79_plugin_runtime import validate


def test_phase_79_validation_script():
    failures = validate()
    assert failures == []
