import subprocess


def test_script_help():
    res = subprocess.run(["./scripts/validate-real-providers-e2e.sh", "--help"], capture_output=True, text=True)
    assert "Usage:" in res.stdout

def test_script_dry_run(tmp_path):
    out_dir = tmp_path / "e2e"
    res = subprocess.run([
        "./scripts/validate-real-providers-e2e.sh",
        "--dry-run",
        "--output-dir", str(out_dir)
    ], capture_output=True, text=True)
    assert res.returncode == 0
    assert "E2E Status:" in res.stdout
    assert "REAL_PROVIDER_E2E_PASS" in res.stdout
