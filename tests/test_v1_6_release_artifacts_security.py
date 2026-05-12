import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

V1_6_RELEASE_DIRS = [
    "releases/v1.6.0-openai-compat",
    "releases/v1.6.1-openai-compat",
    "releases/v1.6.1-product-hardening",
    "releases/v1.6.2-installer-polish",
    "releases/v1.6.3-readiness-cleanup",
    "releases/v1.6.4-customer-demo-pack",
    "releases/v1.6.5-sales-ops",
    "v1.6.6-repo-cleanup",
]

RELEASE_ARTIFACT_FILES = [
    "release-manifest.json",
    "bundle-manifest.json",
    "summary.json",
    "summary.md",
]

SECRET_PATTERNS = [
    "sk-",
    "ghp_",
    "ADMIN_TOKEN=",
    "JWT_SECRET=",
    "-----BEGIN",
]

SECRET_ALLOW_LIST = [
    "__redacted__",
    "sk-demo",
    "sk-local-example",
    "admin-token-123",
    "example",
    "changeme",
    "localhost",
]


def get_existing_release_dirs():
    existing = []
    release_base = ROOT / "releases"
    if not release_base.exists():
        return existing
    for d in release_base.iterdir():
        if d.is_dir() and d.name.startswith("v1.6"):
            existing.append(d)
    return existing


def test_no_tar_gz_in_release_dirs():
    for rel_dir in get_existing_release_dirs():
        tarballs = list(rel_dir.glob("*.tar.gz"))
        assert not tarballs, (
            f".tar.gz found in {rel_dir.name}: {[f.name for f in tarballs]}"
        )


def test_no_pem_key_in_release_dirs():
    for rel_dir in get_existing_release_dirs():
        pem_files = list(rel_dir.glob("*.pem"))
        key_files = list(rel_dir.glob("*.key"))
        forbidden = pem_files + key_files
        assert not forbidden, (
            f"Sensitive files found in {rel_dir.name}: {[f.name for f in forbidden]}"
        )


def test_no_env_files_in_release_dirs():
    for rel_dir in get_existing_release_dirs():
        env_files = list(rel_dir.glob(".env*"))
        assert not env_files, (
            f".env files found in {rel_dir.name}: {[f.name for f in env_files]}"
        )


def test_no_secrets_in_manifests():
    for rel_dir in get_existing_release_dirs():
        for file_pattern in RELEASE_ARTIFACT_FILES:
            for artifact_file in rel_dir.glob(file_pattern):
                content = artifact_file.read_text(encoding="utf-8", errors="ignore")
                for pat in SECRET_PATTERNS:
                    if pat in content:
                        for allow in SECRET_ALLOW_LIST:
                            if allow in content:
                                break
                        else:
                            lines = content.splitlines()
                            for i, line in enumerate(lines, 1):
                                if pat in line:
                                    assert False, (
                                        f"Secret pattern '{pat}' found in "
                                        f"{rel_dir.name}/{artifact_file.name}:{i}"
                                    )


def test_summary_json_has_no_test_tokens():
    for rel_dir in get_existing_release_dirs():
        summary_json = rel_dir / "summary.json"
        if not summary_json.exists():
            continue

        data = json.loads(summary_json.read_text(encoding="utf-8"))
        serialized = json.dumps(data)

        token_patterns = ["sk-", "ghp_", "test-token", "fake-token"]
        for pat in token_patterns:
            if pat in serialized:
                for allow in ["__redacted__", "sk-demo", "sk-local-example"]:
                    if allow in serialized:
                        break
                else:
                    assert False, (
                        f"Token pattern '{pat}' found in "
                        f"{rel_dir.name}/summary.json"
                    )


def test_release_manifest_no_sensitive_fields():
    for rel_dir in get_existing_release_dirs():
        manifest_path = rel_dir / "release-manifest.json"
        if not manifest_path.exists():
            continue

        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        sensitive_keys = ["admin_token", "api_key", "password", "private_key"]
        serialized = json.dumps(data)
        for key in sensitive_keys:
            assert key not in serialized, (
                f"Sensitive key pattern '{key}' found in "
                f"{rel_dir.name}/release-manifest.json"
            )


def test_no_logs_dir_in_releases():
    for rel_dir in get_existing_release_dirs():
        logs_dir = rel_dir / "logs"
        assert not logs_dir.exists(), (
            f"logs/ directory found in {rel_dir.name} (should not be versioned)"
        )


def test_gitignore_excludes_release_tarballs():
    gitignore = ROOT / ".gitignore"
    assert gitignore.exists(), ".gitignore missing"
    content = gitignore.read_text(encoding="utf-8")
    assert "releases/**/*.tar.gz" in content, (
        ".gitignore missing 'releases/**/*.tar.gz' rule"
    )


def test_check_secrets_script_passes_on_releases():
    result = subprocess.run(
        ["./scripts/check-secrets.sh", "--path", "releases"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"check-secrets.sh --path releases failed:\n{result.stdout}\n{result.stderr}"
    )
