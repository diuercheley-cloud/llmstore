import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_scripts_exist_and_executable():
    scripts = [
        "scripts/seed-demo-local.sh",
        "scripts/reset-demo-local.sh",
        "scripts/validate-demo-local.sh"
    ]
    for script_path in scripts:
        full_path = ROOT / script_path
        assert full_path.exists(), f"{script_path} does not exist"
        assert os.access(full_path, os.X_OK), f"{script_path} is not executable"

def test_demo_documents_exist():
    docs_dir = ROOT / "demo" / "rag-documents"
    assert docs_dir.is_dir()
    expected_files = ["demo_empresa.txt", "demo_politicas.txt", "demo_produtos.txt"]
    for f in expected_files:
        assert (docs_dir / f).exists()

def test_seed_script_requires_admin_token():
    # Run with empty environment and a fake empty env file to avoid loading defaults
    env = os.environ.copy()
    if "ADMIN_TOKEN" in env:
        del env["ADMIN_TOKEN"]
    env["ENV_FILE"] = "/dev/null"
    
    result = subprocess.run(
        ["./scripts/seed-demo-local.sh"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env
    )
    assert result.returncode != 0
    assert "ADMIN_TOKEN" in result.stdout or "ADMIN_TOKEN" in result.stderr
