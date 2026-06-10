import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "FRESH_MACHINE_VALIDATION.md"
SCRIPT = ROOT / "scripts" / "fresh-machine-readiness-check.sh"
VALIDATE_SCRIPT = ROOT / "scripts" / "validate-fresh-machine-docs.sh"


def test_document_exists():
    assert DOC.exists(), "FRESH_MACHINE_VALIDATION.md not found"


def test_document_has_objective():
    content = DOC.read_text(encoding="utf-8")
    assert "Objetivo" in content or "objetivo" in content


def test_document_has_prerequisites():
    content = DOC.read_text(encoding="utf-8")
    assert "Pré-requisitos" in content or "pré-requisitos" in content


def test_document_has_acceptance_checklist():
    content = DOC.read_text(encoding="utf-8")
    assert "Checklist de Aceite" in content


def test_document_mentions_no_auto_download():
    content = DOC.read_text(encoding="utf-8")
    has_portuguese = "não baixa modelos" in content or "nunca baixa modelos" in content
    has_english = "not download model" in content or "no auto download" in content
    has_checklist = "Nenhum modelo baixado automaticamente" in content
    assert has_portuguese or has_english or has_checklist, (
        "Document does not state that models are not auto-downloaded"
    )


def test_document_mentions_psp_pix():
    content = DOC.read_text(encoding="utf-8")
    assert "PSP" in content or "PIX" in content, (
        "Document does not mention PSP/PIX out of scope"
    )


def test_document_mentions_wsl2_linux():
    content = DOC.read_text(encoding="utf-8")
    assert "WSL2" in content or "WSL" in content or "Linux" in content, (
        "Document does not mention WSL2/Linux"
    )


def test_document_has_troubleshooting():
    content = DOC.read_text(encoding="utf-8")
    assert "Troubleshooting" in content or "troubleshooting" in content


def test_document_has_install_appliance_section():
    content = DOC.read_text(encoding="utf-8")
    assert "install-local-appliance.sh" in content


def test_document_no_secrets():
    content = DOC.read_text(encoding="utf-8")
    secret_patterns = [
        r"sk-[a-zA-Z0-9]{20,}",
        r"ghp_[a-zA-Z0-9]{36}",
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    ]
    for pat in secret_patterns:
        matches = re.findall(pat, content)
        assert not matches, f"Secret pattern '{pat}' found in document: {matches}"


def test_script_help_works():
    assert SCRIPT.exists()
    result = subprocess.run(
        ["bash", str(SCRIPT), "--help"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0
    assert "Usage:" in result.stdout


def test_validate_script_works():
    assert VALIDATE_SCRIPT.exists()
    assert os.access(VALIDATE_SCRIPT, os.X_OK)


def test_validate_script_run(tmp_path):
    result = subprocess.run(
        ["bash", str(VALIDATE_SCRIPT)],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, f"validate script failed:\n{result.stdout}\n{result.stderr}"
