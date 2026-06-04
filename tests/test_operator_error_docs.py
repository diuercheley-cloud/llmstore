import re
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
DOCS_PATH = ROOT_DIR / "docs" / "OPERATOR_ERROR_CODES.md"
SCRIPTS_DIR = ROOT_DIR / "scripts"

def test_docs_exists():
    assert DOCS_PATH.exists()

def test_essential_codes_in_docs():
    content = DOCS_PATH.read_text()
    essential_codes = [
        "DOCKER_NOT_RUNNING",
        "PORT_IN_USE",
        "ENV_MISSING",
        "HEALTH_FAILED",
        "VALIDATION_FAILED",
        "SECURITY_FAILED",
        "UPGRADE_FAILED",
        "ROLLBACK_FAILED"
    ]
    for code in essential_codes:
        assert f"**{code}**" in content

def test_scripts_use_standard_codes():
    # Find all codes used in scripts via operator_error/warning
    codes_used = set()
    for script in SCRIPTS_DIR.glob("*.sh"):
        content = script.read_text(errors='ignore')
        matches = re.findall(r'operator_(?:error|warning)\s+"([^"]+)"', content)
        codes_used.update(matches)
    
    # Ensure they are in the docs
    docs_content = DOCS_PATH.read_text()
    for code in codes_used:
        # TEST_CODE is used in validation script, we can skip it or add it to docs
        if code == "TEST_CODE":
            continue
        assert code in docs_content, f"Code {code} used in scripts but not documented in {DOCS_PATH.name}"
