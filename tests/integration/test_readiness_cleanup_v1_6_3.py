from pathlib import Path


def test_readiness_cleanup_script_exists():
    script_path = Path("scripts/legacy/validate-readiness-cleanup-v1.6.3.sh")
    assert script_path.exists(), "O script validate-readiness-cleanup-v1.6.3.sh deve existir"


def test_readiness_cleanup_docs_exist():
    doc_path = Path("docs/READINESS_CLEANUP_v1.6.3.md")
    assert doc_path.exists(), "O documento READINESS_CLEANUP_v1.6.3.md deve existir"
