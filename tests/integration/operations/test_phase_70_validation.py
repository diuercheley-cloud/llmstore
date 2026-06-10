import subprocess
from pathlib import Path


def test_phase_70_validation_script():
    """
    Executes the Phase 70 validation script and ensures it passes.
    This verifies that all required components are in place and follow architectural rules.
    """
    script_path = Path("scripts/validators/validate_phase_70_correlation_engine.py")
    assert script_path.exists(), "Validation script missing"
    
    # Run the script using the current python interpreter
    result = subprocess.run(
        ["python3", str(script_path)],
        capture_output=True,
        text=True
    )
    
    # Print output for debugging in case of failure
    if result.returncode != 0:
        print("\n--- Validation Script Output ---")
        print(result.stdout)
        print(result.stderr)
    
    assert result.returncode == 0, f"Phase 70 validation failed with code {result.returncode}"
    assert "Phase 70 Validation: SUCCESS" in result.stdout

def test_docs_contain_mandatory_sections():
    """
    Ensures the Phase 70 documentation contains all required architectural sections.
    """
    docs_path = Path("docs/operations/operations_correlation_engine.md")
    assert docs_path.exists(), "Documentation missing"
    
    content = docs_path.read_text()
    required_sections = [
        "Architecture Overview",
        "Correlation Engine",
        "Trust Graph",
        "Receipts",
        "Audit Events",
        "APIs",
        "Dashboard",
        "Limitations",
        "Offline Compatibility",
        "Security Notes"
    ]
    
    for section in required_sections:
        assert section in content, f"Missing section '{section}' in documentation"

def test_api_portability_and_advisory_status():
    """
    Checks the API files to ensure they enforce the advisory-only status
    and don't include forbidden enforcement functions.
    """
    admin_api = Path("control_plane/app/api/operations_correlation_admin.py")
    portal_api = Path("control_plane/app/api/operations_correlation_portal.py")
    
    for api_path in [admin_api, portal_api]:
        assert api_path.exists()
        content = api_path.read_text()
        assert "advisory_only" in content.lower(), f"Missing advisory_only in {api_path}"
        
        # Prohibited enforcement actions
        forbidden = ["block_client", "suspend_account", "terminate_session"]
        for f in forbidden:
            assert f not in content, f"Forbidden enforcement action '{f}' found in {api_path}"
