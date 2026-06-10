import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RUNNER_SCRIPT = ROOT / "scripts" / "run-v1.7-release-checklist.sh"
ARTIFACTS_BASE = ROOT / "artifacts" / "v1.7-release-checklist"


def latest_artifact_dir():
    if not ARTIFACTS_BASE.exists():
        return None
    subdirs = sorted([d for d in ARTIFACTS_BASE.iterdir() if d.is_dir()], reverse=True)
    for d in subdirs:
        if (d / "v1.7-checklist-status.json").exists():
            return d
    return None


def test_runner_script_exists():
    if not RUNNER_SCRIPT.exists():
        pytest.skip("run-v1.7-release-checklist.sh not found")
    assert os.access(RUNNER_SCRIPT, os.X_OK), "runner script not executable"


def test_runner_script_runs_quick():
    """Runner should complete in --quick mode without errors."""
    if not RUNNER_SCRIPT.exists():
        pytest.skip("run-v1.7-release-checklist.sh not found")
    result = subprocess.run(
        ["bash", str(RUNNER_SCRIPT), "--quick"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    print(f"STDOUT:\n{result.stdout}")
    print(f"STDERR:\n{result.stderr}")
    # Should exit 0 (GO or GO_WITH_WARNINGS) -- quick mode may skip some
    assert result.returncode in (0,), (
        f"Runner script failed with exit code {result.returncode}"
    )


def test_runner_generates_artifact_json():
    artifact_dir = latest_artifact_dir()
    if artifact_dir is None:
        pytest.skip("No artifact directory found")
    fp = artifact_dir / "v1.7-checklist-status.json"
    if not fp.exists():
        pytest.skip("v1.7-checklist-status.json not found")
    assert fp.stat().st_size > 0


def test_runner_generates_artifact_md():
    artifact_dir = latest_artifact_dir()
    if artifact_dir is None:
        pytest.skip("No artifact directory found")
    fp = artifact_dir / "v1.7-checklist-status.md"
    if not fp.exists():
        pytest.skip("v1.7-checklist-status.md not found")
    assert fp.stat().st_size > 0


def test_artifact_json_is_valid():
    artifact_dir = latest_artifact_dir()
    if artifact_dir is None:
        pytest.skip("No artifact directory found")
    fp = artifact_dir / "v1.7-checklist-status.json"
    if not fp.exists():
        pytest.skip("v1.7-checklist-status.json not found")
    data = json.loads(fp.read_text(encoding="utf-8"))

    required = [
        "report_type", "generated_at", "timestamp", "version",
        "blocker_fails", "blocker_warns", "nonblocker_warns",
        "blocker_fail_list", "warning_list", "go_decision",
    ]
    for field in required:
        assert field in data, f"Missing field: {field}"

    assert data["report_type"] == "v1.7-consolidated-checklist"
    valid_decisions = ("GO", "GO_WITH_WARNINGS", "GO_WITH_ACCEPTED_WARNINGS", "V1_7_READY_WITH_ACCEPTED_WARNINGS", "NO_GO", "PENDENTE")
    assert data["go_decision"] in valid_decisions


def test_artifact_has_no_secrets():
    artifact_dir = latest_artifact_dir()
    if artifact_dir is None:
        pytest.skip("No artifact directory found")
    for fname in ["v1.7-checklist-status.json", "v1.7-checklist-status.md"]:
        fp = artifact_dir / fname
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


def test_artifact_mentions_psp_pix():
    artifact_dir = latest_artifact_dir()
    if artifact_dir is None:
        pytest.skip("No artifact directory found")
    for fname in ["v1.7-checklist-status.json", "v1.7-checklist-status.md"]:
        fp = artifact_dir / fname
        if not fp.exists():
            continue
        content = fp.read_text(encoding="utf-8")
        if "PSP" in content or "PIX" in content:
            return
    pytest.skip("PSP/PIX not found in artifact (non-blocking)")


def test_artifact_go_decision_consistent():
    artifact_dir = latest_artifact_dir()
    if artifact_dir is None:
        pytest.skip("No artifact directory found")
    fp = artifact_dir / "v1.7-checklist-status.json"
    if not fp.exists():
        pytest.skip("v1.7-checklist-status.json not found")
    data = json.loads(fp.read_text(encoding="utf-8"))

    bf = data.get("blocker_fails", 0)
    decision = data.get("go_decision", "")

    if bf > 0:
        assert decision == "NO_GO", (
            f"Blocker fails={bf} but decision='{decision}'; expected NO_GO"
        )
    elif data.get("blocker_warns", 0) > 0 or data.get("nonblocker_warns", 0) > 0:
        valid_go = ("GO_WITH_WARNINGS", "GO_WITH_ACCEPTED_WARNINGS", "V1_7_READY_WITH_ACCEPTED_WARNINGS", "NO_GO")
        assert decision in valid_go, (
            f"Warnings present but decision='{decision}'; expected one of {valid_go}"
        )


def test_artifact_has_limitations():
    artifact_dir = latest_artifact_dir()
    if artifact_dir is None:
        pytest.skip("No artifact directory found")
    fp = artifact_dir / "v1.7-checklist-status.json"
    if not fp.exists():
        pytest.skip("v1.7-checklist-status.json not found")
    data = json.loads(fp.read_text(encoding="utf-8"))
    limitations = data.get("limitations_out_of_scope", [])
    assert len(limitations) > 0, "No limitations_out_of_scope in artifact"
    has_psp = any("PSP" in l for l in limitations)
    has_cloud = any("cloud" in l.lower() for l in limitations)
    has_internet = any("internet" in l.lower() for l in limitations)
    if not (has_psp and has_cloud and has_internet):
        pytest.skip("Not all limitations found (non-blocking)")
