import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CHECK_SECRETS = ROOT / "scripts" / "check-secrets.sh"
RELEASE_DIR = ROOT / "releases" / "v1.7.0-local-ai-appliance"
VERSION = "v1.7.0-local-ai-appliance"

SECRET_PATTERNS = [
    ("sk-", "OpenAI API key"),
    ("ghp_", "GitHub token"),
    ("ADMIN_TOKEN=", "Admin token"),
    ("JWT_SECRET=", "JWT secret"),
    ("-----BEGIN ", "Private key"),
]
SAFE_ALLOWS = ["__redacted__", "sk-demo", "sk-local-example", "redacted"]


def test_check_secrets_script_exists():
    assert CHECK_SECRETS.exists(), "check-secrets.sh not found"
    assert os.access(CHECK_SECRETS, os.X_OK), "check-secrets.sh not executable"


def test_check_secrets_all_passes():
    """check-secrets --all must return exit code 0."""
    result = subprocess.run(
        ["bash", str(CHECK_SECRETS), "--all"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    print(f"STDOUT:\n{result.stdout}")
    assert result.returncode == 0, f"check-secrets --all failed:\n{result.stdout}"


def test_check_secrets_release_dir():
    """check-secrets on release dir must pass."""
    if not RELEASE_DIR.exists():
        pytest.skip("Release dir not found")
    result = subprocess.run(
        ["bash", str(CHECK_SECRETS), "--path", str(RELEASE_DIR)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    print(f"STDOUT:\n{result.stdout}")
    assert result.returncode == 0, f"check-secrets on release dir failed:\n{result.stdout}"


def test_release_dir_no_tar_gz():
    """Release dir must not contain .tar.gz files."""
    if not RELEASE_DIR.exists():
        pytest.skip("Release dir not found")
    tar_files = list(RELEASE_DIR.glob("*.tar.gz"))
    assert len(tar_files) == 0, f".tar.gz found: {tar_files}"


def test_release_dir_no_forbidden_files():
    """Release dir must not contain .env, .pem, .key, .crt files."""
    if not RELEASE_DIR.exists():
        pytest.skip("Release dir not found")
    for f in RELEASE_DIR.iterdir():
        if f.is_file():
            for ext in [".env", ".pem", ".key", ".crt"]:
                assert not f.name.endswith(ext), f"Forbidden file: {f.name}"
            assert f.name not in (".env", ".env.local"), f"Forbidden file: {f.name}"


def test_release_dir_security():
    """Release dir must have exactly 5 safe files with no secrets."""
    if not RELEASE_DIR.exists():
        pytest.skip("Release dir not found")
    files = [f for f in RELEASE_DIR.iterdir() if f.is_file()]
    assert len(files) == 5, f"Expected 5 files, got {len(files)}: {[f.name for f in files]}"

    for fp in files:
        content = fp.read_text(encoding="utf-8")
        for pat, name in SECRET_PATTERNS:
            if pat in content:
                for allow in SAFE_ALLOWS:
                    if allow in content:
                        break
                else:
                    assert False, f"Secret '{pat}' ({name}) in {fp.name}"


def test_bundle_manifest_security():
    """bundle-manifest.json must confirm security scan passed."""
    fp = RELEASE_DIR / "bundle-manifest.json"
    if not fp.exists():
        pytest.skip("bundle-manifest.json not found")
    data = json.loads(fp.read_text(encoding="utf-8"))
    assert data.get("secrets_scan_passed") is True
    assert data.get("models_included") is False
    assert data.get("rag_uploads_included") is False
    assert data.get("env_included") is False
    assert data.get("local_data_included") is False


def test_release_manifest_validation():
    """release-manifest.json must show validation_result=success."""
    fp = RELEASE_DIR / "release-manifest.json"
    if not fp.exists():
        pytest.skip("release-manifest.json not found")
    data = json.loads(fp.read_text(encoding="utf-8"))
    assert data.get("validation_result") == "success"


def test_no_models_in_bundle():
    """Release must not include models or rag data."""
    fp = RELEASE_DIR / "bundle-manifest.json"
    if not fp.exists():
        pytest.skip("bundle-manifest.json not found")
    data = json.loads(fp.read_text(encoding="utf-8"))
    excluded = data.get("excluded_paths", [])
    assert "models" in excluded, "models not excluded"
    assert "data/rag_uploads" in excluded, "rag_uploads not excluded"
    assert "*.gguf" in excluded, "*.gguf not excluded"
    assert "backups" in excluded, "backups not excluded"
    assert "exports" in excluded, "exports not excluded"


def test_checksums_no_secrets():
    """Checksums file must be safe (hash + filename only)."""
    fp = RELEASE_DIR / "bundle-checksums.sha256"
    if not fp.exists():
        pytest.skip("bundle-checksums.sha256 not found")
    content = fp.read_text(encoding="utf-8").strip()
    for line in content.split("\n"):
        parts = line.strip().split()
        assert len(parts) == 2, f"Invalid checksum line: {line}"
        assert len(parts[0]) == 64, "Hash not 64 hex chars"
        try:
            int(parts[0], 16)
        except ValueError:
            assert False, "Invalid hex in checksum"
        assert parts[1].endswith(".tar.gz"), "Filename must end with .tar.gz"
        # No secret patterns in filename
        for pat in ["sk-", "ghp_", "token"]:
            assert pat not in parts[1], f"Secret pattern in filename: {pat}"


def test_summary_no_secrets():
    """summary.json and summary.md must not contain secrets."""
    for fname in ["summary.json", "summary.md"]:
        fp = RELEASE_DIR / fname
        if not fp.exists():
            continue
        content = fp.read_text(encoding="utf-8")
        for pat, name in SECRET_PATTERNS:
            if pat in content:
                for allow in SAFE_ALLOWS:
                    if allow in content:
                        break
                else:
                    assert False, f"Secret '{pat}' in {fname}"


def test_final_validation_report_no_secrets():
    """Latest final validation report must be clean."""
    base = ROOT / "artifacts" / "v1.7-final-validation"
    if not base.exists():
        pytest.skip("No final validation artifacts")
    subdirs = sorted([d for d in base.iterdir() if d.is_dir()])
    if not subdirs:
        pytest.skip("No final validation directories")
    latest = subdirs[-1]
    for fname in ["v1.7-final-validation.json", "v1.7-final-validation.md"]:
        fp = latest / fname
        if not fp.exists():
            continue
        content = fp.read_text(encoding="utf-8")
        for pat, name in SECRET_PATTERNS:
            if pat in content:
                for allow in SAFE_ALLOWS:
                    if allow in content:
                        break
                else:
                    assert False, f"Secret '{pat}' in final report {fname}"


def test_security_report_artifact_exists():
    """Check if a security report was generated (non-blocking)."""
    sec_reports = ROOT / "artifacts" / "security-reports"
    if not sec_reports.exists() or not list(sec_reports.iterdir()):
        pytest.skip("No security reports found")
    latest_sec = sorted([d for d in sec_reports.iterdir() if d.is_dir()])
    if latest_sec:
        latest = latest_sec[-1]
        json_file = latest / "security-report.json"
        if json_file.exists():
            data = json.loads(json_file.read_text(encoding="utf-8"))
            score = data.get("score", "")
            assert score in ["PASS", "PASS_WITH_WARNINGS"], f"Security score not PASS: {score}"
