import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "validate-commercial-demo-e2e-local.sh"


def test_script_exists():
    assert SCRIPT.exists(), "validate-commercial-demo-e2e-local.sh missing"
    assert os.access(SCRIPT, os.X_OK), "script not executable"


def test_help_flag():
    result = subprocess.run(
        ["bash", str(SCRIPT), "--help"],
        cwd=ROOT, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0
    output = result.stdout.lower()
    assert "usage" in output or "demo" in output
    assert "--seed-demo" in output
    assert "--base-url" in output
    assert "--skip-tts" in output
    assert "--skip-rag" in output


def test_unknown_flag():
    result = subprocess.run(
        ["bash", str(SCRIPT), "--unknown-flag"],
        cwd=ROOT, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode != 0


def test_base_url_flag():
    result = subprocess.run(
        ["bash", str(SCRIPT), "--base-url", "http://localhost:99999", "--help"],
        cwd=ROOT, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0


def test_script_has_required_steps():
    content = SCRIPT.read_text(encoding="utf-8")
    steps = [
        "Checking stack is up",
        "Seeding commercial demo pack",
        "Validating fake demo data",
        "meeting-ready",
        "capabilities",
        "landing page",
        "Admin Dashboard",
        "Client Portal",
        "Admin Lab",
        "CRM",
        "demo proposal",
        "demo quote",
        "demo SOW",
        "demo monthly report",
        "chat completion",
        "/v1/responses",
        "/v1/embeddings",
        "RAG",
        "TTS",
        "billing",
        "check-secrets",
        "Generating report",
    ]
    for step_name in steps:
        assert step_name.lower() in content.lower(), f"Step '{step_name}' not found in script"
