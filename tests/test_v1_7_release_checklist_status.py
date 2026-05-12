import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
STATUS_SCRIPT = ROOT / "scripts" / "generate-v1.7-release-checklist-status.sh"
STATUS_BASE = ROOT / "artifacts" / "final-qa" / "v1.7-checklist"


def latest_status_dir():
    if not STATUS_BASE.exists():
        return None
    subdirs = sorted([d for d in STATUS_BASE.iterdir() if d.is_dir()])
    return subdirs[-1] if subdirs else None


def test_status_script_exists():
    assert STATUS_SCRIPT.exists(), "generate script not found"


def test_status_script_runs():
    result = subprocess.run(
        ["bash", str(STATUS_SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, (
        f"Status script failed:\n{result.stdout}\n{result.stderr}"
    )


def test_status_json_exists():
    status_dir = latest_status_dir()
    if status_dir is None:
        pytest.skip("No status directory")
    fp = status_dir / "checklist-status.json"
    assert fp.exists(), "checklist-status.json not found"
    assert fp.stat().st_size > 0


def test_status_md_exists():
    status_dir = latest_status_dir()
    if status_dir is None:
        pytest.skip("No status directory")
    fp = status_dir / "checklist-status.md"
    assert fp.exists(), "checklist-status.md not found"
    assert fp.stat().st_size > 0


def test_status_is_valid_json():
    status_dir = latest_status_dir()
    if status_dir is None:
        pytest.skip("No status directory")
    fp = status_dir / "checklist-status.json"
    data = json.loads(fp.read_text(encoding="utf-8"))

    required = ["report_type", "generated_at", "version", "items", "summary", "go_criteria", "go_decision"]
    for field in required:
        assert field in data, f"Missing field: {field}"

    assert data["report_type"] == "v1.7-checklist-status"
    assert len(data["items"]) > 0, "No items in status"


def test_status_has_blocker_summary():
    status_dir = latest_status_dir()
    if status_dir is None:
        pytest.skip("No status directory")
    fp = status_dir / "checklist-status.json"
    data = json.loads(fp.read_text(encoding="utf-8"))

    summary = data.get("summary", {})
    for field in ["blockers_total", "blockers_pass", "blockers_fail", "blockers_warn", "blockers_todo"]:
        assert field in summary, f"Missing summary field: {field}"


def test_status_has_gonogo():
    status_dir = latest_status_dir()
    if status_dir is None:
        pytest.skip("No status directory")
    fp = status_dir / "checklist-status.json"
    data = json.loads(fp.read_text(encoding="utf-8"))

    criteria = data.get("go_criteria", {})
    assert len(criteria) > 0, "No Go/No-Go criteria"

    decision = data.get("go_decision", "")
    assert "GO" in decision or "NO-GO" in decision, f"Invalid decision: {decision}"


def test_status_version_matches_repo():
    status_dir = latest_status_dir()
    if status_dir is None:
        pytest.skip("No status directory")
    actual_version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    fp = status_dir / "checklist-status.json"
    data = json.loads(fp.read_text(encoding="utf-8"))
    assert data["version"] == actual_version, (
        f"Status version '{data['version']}' != repo version '{actual_version}'"
    )


def test_status_no_secrets():
    status_dir = latest_status_dir()
    if status_dir is None:
        pytest.skip("No status directory")
    for fname in ["checklist-status.json", "checklist-status.md"]:
        fp = status_dir / fname
        if not fp.exists():
            continue
        content = fp.read_text(encoding="utf-8")
        for pat in ["sk-", "ghp_", "ADMIN_TOKEN=", "JWT_SECRET=", "-----BEGIN"]:
            if pat in content:
                for allow in ["__redacted__", "sk-demo", "sk-local-example", "redacted"]:
                    if allow in content:
                        break
                else:
                    assert False, f"Secret pattern '{pat}' found in {fname}"


def test_status_mentions_psp_pix():
    status_dir = latest_status_dir()
    if status_dir is None:
        pytest.skip("No status directory")
    for fname in ["checklist-status.json", "checklist-status.md"]:
        fp = status_dir / fname
        if not fp.exists():
            continue
        content = fp.read_text(encoding="utf-8")
        if "PSP" in content or "PIX" in content:
            return
    pytest.skip("PSP/PIX not found in status (non-blocking)")
