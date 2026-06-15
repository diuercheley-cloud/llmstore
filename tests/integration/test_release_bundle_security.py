import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def security_trap_env():
    # Create some files that should be excluded or caught
    traps = {
        "models/trap.gguf": "fake model",
        ".env": "SECRET_KEY=12345",
        "data/rag_uploads/secret.txt": "sensitive rag data",
        "control_plane/app/secret.pem": "fake pem",
    }

    created_files = []
    for path, content in traps.items():
        p = Path(path)
        if not p.parent.exists():
            p.parent.mkdir(parents=True)
        # If file exists, back it up? No, this is a test env, but let's be careful
        backup = None
        if p.exists():
            backup = Path(str(p) + ".bak_test")
            shutil.copy(p, backup)

        p.write_text(content)
        created_files.append((p, backup))

    yield

    for p, backup in created_files:
        if p.exists():
            p.unlink()
        if backup and backup.exists():
            shutil.move(backup, p)


def test_security_exclusions(security_trap_env):
    version = "v-security-test"
    # Ensure cleanup before
    if Path(f"releases/{version}").exists():
        shutil.rmtree(f"releases/{version}")

    # We expect it to succeed in creating the bundle because it should EXCLUDE these files
    # except for things inside source code that check-secrets might catch

    # Actually, control_plane/app/secret.pem SHOULD be excluded by extension check in create-release-bundle.sh
    # But if I put a real-looking secret in a .py file, it should FAIL the bundle creation.

    # Let's test exclusion first
    cmd = ["./scripts/release/create-release-bundle.sh", "--version", version]
    subprocess.run(cmd, check=True)

    import tarfile

    archive_path = Path(f"releases/{version}/llm-inference-stack-{version}.tar.gz")
    with tarfile.open(archive_path, "r:gz") as tar:
        names = tar.getnames()
        root = f"llm-inference-stack-{version}"
        assert f"{root}/models/trap.gguf" not in names
        assert f"{root}/.env" not in names
        assert f"{root}/data/rag_uploads/secret.txt" not in names
        assert f"{root}/control_plane/app/secret.pem" not in names


def test_secrets_scan_failure(tmp_path):
    # If a secret is found in a file that IS included, it should fail.
    # We need to simulate this by creating a file in a path that is included.

    # We'll use a sub-directory and copy the script there to avoid messing with the real project
    # Or just use the real project but be VERY careful.

    trap_file = Path("control_plane/app/trap_secret.py")
    fake_key = "sk-" + "12345678901234567890123456789012"
    trap_file.write_text("API_" + "KEY = '" + fake_key + "'")

    try:
        version = "v-fail-test"
        cmd = ["./scripts/release/create-release-bundle.sh", "--version", version]
        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode != 0
        assert "Secrets detected in the staging directory" in result.stdout
    finally:
        if trap_file.exists():
            trap_file.unlink()
