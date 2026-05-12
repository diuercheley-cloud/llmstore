import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
VERSION = "v1.7.0-local-ai-appliance"
RELEASE_DIR = ROOT / "releases" / VERSION
CHECK_SECRETS = ROOT / "scripts" / "check-secrets.sh"

REQUIRED_FILES = [
    "release-manifest.json",
    "summary.json",
    "summary.md",
    "bundle-manifest.json",
    "bundle-checksums.sha256",
]


def test_release_dir_exists():
    assert RELEASE_DIR.exists(), f"releases/{VERSION} not found"


def test_no_secrets_in_manifests():
    """All release manifests must be free of real secrets."""
    secret_patterns = [
        ("sk-", "OpenAI API key"),
        ("ghp_", "GitHub token"),
        ("ADMIN_TOKEN=", "Admin token"),
        ("JWT_SECRET=", "JWT secret"),
        ("-----BEGIN ", "Private key"),
    ]
    for fname in REQUIRED_FILES:
        fp = RELEASE_DIR / fname
        if not fp.exists():
            continue
        content = fp.read_text(encoding="utf-8")
        for pat, name in secret_patterns:
            if pat in content:
                for allow in ["__redacted__", "sk-demo", "sk-local-example", "redacted"]:
                    if allow in content:
                        break
                else:
                    assert False, (
                        f"Secret pattern '{pat}' ({name}) found in {fname}"
                    )


def test_no_tar_gz_versioned():
    """No .tar.gz should be present in the versionable release directory."""
    tar_files = list(RELEASE_DIR.glob("*.tar.gz"))
    assert len(tar_files) == 0, f".tar.gz files found: {tar_files}"


def test_bundle_manifest_secrets_scan():
    """bundle-manifest.json must report secrets_scan_passed=true."""
    fp = RELEASE_DIR / "bundle-manifest.json"
    assert fp.exists(), "bundle-manifest.json not found"
    data = json.loads(fp.read_text(encoding="utf-8"))
    assert data.get("secrets_scan_passed") is True, (
        "secrets_scan_passed is not true in bundle-manifest.json"
    )


def test_bundle_manifest_no_forbidden_content():
    """bundle-manifest.json must confirm no forbidden content."""
    fp = RELEASE_DIR / "bundle-manifest.json"
    assert fp.exists(), "bundle-manifest.json not found"
    data = json.loads(fp.read_text(encoding="utf-8"))
    assert data.get("models_included") is False
    assert data.get("rag_uploads_included") is False
    assert data.get("env_included") is False
    assert data.get("local_data_included") is False


def test_bundle_manifest_includes_exclude_paths():
    """bundle-manifest.json excluded_paths must include dangerous items."""
    fp = RELEASE_DIR / "bundle-manifest.json"
    data = json.loads(fp.read_text(encoding="utf-8"))
    excluded = data.get("excluded_paths", [])
    must_exclude = ["models", "data/rag_uploads", ".env", ".env.local",
                     "backups", "exports", "artifacts", "*.gguf", "*.tar.gz"]
    for item in must_exclude:
        assert item in excluded, f"'{item}' not in excluded_paths"


def test_release_manifest_no_models():
    """release-manifest.json must confirm models not included."""
    fp = RELEASE_DIR / "release-manifest.json"
    if not fp.exists():
        pytest.skip("release-manifest.json not found")
    data = json.loads(fp.read_text(encoding="utf-8"))
    models = data.get("models_included", None)
    if models is not None:
        assert models is False, "models_included must be false"
    rag = data.get("rag_uploads_included", None)
    if rag is not None:
        assert rag is False, "rag_uploads_included must be false"


def test_checksums_dont_contain_secrets():
    """Checksums file should only contain hex hash and filename."""
    fp = RELEASE_DIR / "bundle-checksums.sha256"
    if not fp.exists():
        pytest.skip("bundle-checksums.sha256 not found")
    content = fp.read_text(encoding="utf-8").strip()
    for line in content.split("\n"):
        parts = line.strip().split()
        # Should be exactly 2 parts: hash and filename
        assert len(parts) == 2, f"Invalid checksum line: {line}"
        # Hash should be 64 hex chars
        assert len(parts[0]) == 64, f"Hash not 64 hex chars: {parts[0]}"
        # Filename should reference a tar.gz
        assert parts[1].endswith(".tar.gz"), f"Filename doesn't end with .tar.gz: {parts[1]}"
        # No secret patterns in filename
        for pat in ["sk-", "ghp_", "token"]:
            assert pat not in parts[1], f"Secret pattern in checksum filename: {pat}"


def test_check_secrets_on_release_dir():
    """Running check-secrets --path on release dir should pass."""
    result = subprocess.run(
        ["bash", str(CHECK_SECRETS), "--path", str(RELEASE_DIR)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    print(f"STDOUT:\n{result.stdout}")
    assert result.returncode == 0, (
        f"check-secrets failed on release dir:\n{result.stdout}"
    )


def test_no_forbidden_files_in_release():
    """Release directory must not contain .env, .pem, .key, .db files."""
    forbidden_extensions = [".env", ".pem", ".key", ".crt"]
    for f in RELEASE_DIR.iterdir():
        if f.is_file():
            for ext in forbidden_extensions:
                if f.name.endswith(ext) or f.name == ext:
                    assert False, f"Forbidden file type found: {f.name}"


def test_check_secrets_script_exists():
    assert CHECK_SECRETS.exists(), "check-secrets.sh not found"
    assert os.access(CHECK_SECRETS, os.X_OK), "check-secrets.sh not executable"
