
def test_release_script_detects_appliance_mode():
    # We can test if the script contains the expected logic
    with open("scripts/release-local-production.sh", "r") as f:
        content = f.read()
    
    assert "LOCAL_APPLIANCE_MODE" in content
    assert "check-secrets.sh" in content

def test_bundle_script_exclusions():
    # Test that create-release-bundle.sh excludes models and rag_uploads
    with open("scripts/create-release-bundle.sh", "r") as f:
        content = f.read()
    
    assert "\"models\"" in content
    assert "\"data/rag_uploads\"" in content
    assert "\"*.gguf\"" in content

def test_wizard_sets_appliance_mode():
    with open("scripts/configure-local-wizard.sh", "r") as f:
        content = f.read()
    
    assert "update_env \"LOCAL_APPLIANCE_MODE\" \"true\"" in content
