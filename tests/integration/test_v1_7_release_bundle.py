import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
VERSION = "v1.7.0-local-ai-appliance"
RELEASE_DIR = ROOT / "releases" / VERSION
PREPARE_SCRIPT = ROOT / "scripts" / "prepare-v1.7-release-bundle.sh"
VALIDATE_SCRIPT = ROOT / "scripts" / "validate-v1.7-release-bundle.sh"
ARTIFACTS_BASE = ROOT / "artifacts" / "v1.7-release-bundle"

REQUIRED_FILES = [
    "release-manifest.json",
    "summary.json",
    "summary.md",
    "bundle-manifest.json",
    "bundle-checksums.sha256",
]


def test_prepare_script_exists():
    if not PREPARE_SCRIPT.exists():
        pytest.skip("prepare-v1.7-release-bundle.sh not found")
    assert os.access(PREPARE_SCRIPT, os.X_OK), "prepare script not executable"


def test_validate_script_exists():
    if not VALIDATE_SCRIPT.exists():
        pytest.skip("validate-v1.7-release-bundle.sh not found")
    assert os.access(VALIDATE_SCRIPT, os.X_OK), "validate script not executable"


def test_release_dir_exists():
    assert RELEASE_DIR.exists(), f"releases/{VERSION} not found"


def test_required_files_exist():
    missing = [f for f in REQUIRED_FILES if not (RELEASE_DIR / f).exists()]
    assert not missing, f"Missing required files: {missing}"


def test_no_tar_gz_in_release():
    tar_files = list(RELEASE_DIR.glob("*.tar.gz"))
    assert len(tar_files) == 0, f"Found .tar.gz files in release dir: {tar_files}"


def test_bundle_manifest_is_valid_json():
    fp = RELEASE_DIR / "bundle-manifest.json"
    assert fp.exists()
    data = json.loads(fp.read_text(encoding="utf-8"))
    required = ["version", "git_branch", "git_commit", "generated_at",
                 "included_paths", "excluded_paths", "files_count",
                 "archive_name", "archive_sha256", "secrets_scan_passed",
                 "models_included", "rag_uploads_included",
                 "env_included", "local_data_included"]
    for field in required:
        assert field in data, f"Missing field in bundle-manifest.json: {field}"
    assert data["version"] == VERSION, f"Version mismatch: {data['version']}"


def test_release_manifest_is_valid_json():
    fp = RELEASE_DIR / "release-manifest.json"
    assert fp.exists()
    data = json.loads(fp.read_text(encoding="utf-8"))
    required = ["release_name", "version", "git_branch", "git_commit",
                 "generated_at", "validation_artifact_path",
                 "summary_json_path", "summary_md_path"]
    for field in required:
        assert field in data, f"Missing field in release-manifest.json: {field}"


def test_bundle_manifest_no_forbidden_content():
    fp = RELEASE_DIR / "bundle-manifest.json"
    data = json.loads(fp.read_text(encoding="utf-8"))
    assert data.get("models_included") is False, "models should not be included"
    assert data.get("rag_uploads_included") is False, "rag_uploads should not be included"
    assert data.get("env_included") is False, ".env should not be included"
    assert data.get("local_data_included") is False, "local data should not be included"
    assert data.get("secrets_scan_passed") is True, "secrets scan must pass"


def test_checksums_have_valid_format():
    fp = RELEASE_DIR / "bundle-checksums.sha256"
    assert fp.exists()
    content = fp.read_text(encoding="utf-8").strip()
    lines = content.split("\n")
    assert len(lines) >= 1, "checksums file is empty"
    for line in lines:
        parts = line.strip().split()
        assert len(parts) == 2, f"Invalid checksum line: {line}"
        assert len(parts[0]) == 64, f"Invalid hex length: {len(parts[0])}"
        try:
            int(parts[0], 16)
        except ValueError:
            assert False, f"Invalid hex in checksum: {parts[0]}"


def test_summary_json_exists():
    fp = RELEASE_DIR / "summary.json"
    assert fp.exists(), "summary.json not found"
    assert fp.stat().st_size > 0


def test_summary_md_exists():
    fp = RELEASE_DIR / "summary.md"
    assert fp.exists(), "summary.md not found"
    assert fp.stat().st_size > 0


def test_summary_json_is_valid():
    fp = RELEASE_DIR / "summary.json"
    data = json.loads(fp.read_text(encoding="utf-8"))
    required = ["validation_result", "environment", "timestamp"]
    found = [k for k in required if k in data]
    assert len(found) >= 1, f"No expected fields found in summary.json: {found}"


def test_validate_script_runs():
    if not VALIDATE_SCRIPT.exists():
        pytest.skip("validate-v1.7-release-bundle.sh not found")
    result = subprocess.run(
        ["bash", str(VALIDATE_SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    print(f"STDOUT:\n{result.stdout}")
    assert result.returncode == 0, (
        f"validate script failed:\n{result.stdout}\n{result.stderr}"
    )


def test_no_forbidden_dirs_in_release():
    forbidden = [".env", ".env.local", ".local", "models",
                 "data", "backups", "exports"]
    for item in forbidden:
        assert not (RELEASE_DIR / item).exists(), f"Forbidden item found: {item}"


def test_release_file_count():
    files = list(RELEASE_DIR.iterdir())
    # Should be exactly 5: release-manifest.json, summary.json, summary.md,
    # bundle-manifest.json, bundle-checksums.sha256
    file_count = sum(1 for f in files if f.is_file())
    assert file_count == 5, (
        f"Expected 5 files, found {file_count}: {[f.name for f in files if f.is_file()]}"
    )


def test_latest_bundle_report_exists():
    if not ARTIFACTS_BASE.exists():
        pytest.skip("No bundle artifacts base directory")
    subdirs = sorted([d for d in ARTIFACTS_BASE.iterdir() if d.is_dir()])
    if not subdirs:
        pytest.skip("No bundle report directories found")
    latest = subdirs[-1]
    assert (latest / "bundle-report.json").exists(), "bundle-report.json not in latest artifact"
    assert (latest / "bundle-report.md").exists(), "bundle-report.md not in latest artifact"
