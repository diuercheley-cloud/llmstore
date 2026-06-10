import json
import os
import re
import subprocess
from pathlib import Path

SCRIPT_PATH = Path("scripts/dev/diagnose-artifact-secrets.sh")
DOC_PATH = Path("docs/SECURITY_ARTIFACTS_CLEANUP_v1.5.5.md")
UNMASKED_SECRET_RE = re.compile(r"sk-local-[A-Za-z0-9_-]{20,}")


def latest_diagnosis_dir(base_dir: Path) -> Path:
    candidates = sorted(entry for entry in base_dir.iterdir() if entry.is_dir())
    assert candidates
    return candidates[-1]


def test_script_exists_and_executable():
    assert SCRIPT_PATH.exists()
    assert os.access(SCRIPT_PATH, os.X_OK)


def test_help_works():
    result = subprocess.run([str(SCRIPT_PATH), "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "Usage:" in result.stdout


def test_diagnosis_outputs_are_valid_and_masked(tmp_path):
    output_dir = tmp_path / "diagnosis"
    result = subprocess.run(
        [str(SCRIPT_PATH), "--output-dir", str(output_dir)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "JSON Output:" in result.stdout
    assert "MD Output:" in result.stdout
    assert "sk-local-" not in result.stdout

    report_dir = latest_diagnosis_dir(output_dir)
    json_path = report_dir / "diagnosis.json"
    md_path = report_dir / "diagnosis.md"

    assert json_path.exists()
    assert md_path.exists()

    data = json.loads(json_path.read_text())
    assert data["status"] == "open"
    assert data["summary"]["findings"] >= 0
    assert isinstance(data["files"], list)
    assert isinstance(data["findings"], list)

    json_content = json_path.read_text()
    md_content = md_path.read_text()

    assert not UNMASKED_SECRET_RE.search(json_content)
    assert not UNMASKED_SECRET_RE.search(md_content)
    assert "****" in json_content or data["summary"]["findings"] == 0


def test_cleanup_doc_exists():
    assert DOC_PATH.exists()
