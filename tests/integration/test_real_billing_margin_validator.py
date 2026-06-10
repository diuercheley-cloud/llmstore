import os
import subprocess


def test_script_help():
    res = subprocess.run(["./scripts/validators/validate-real-billing-margin.sh", "--help"], capture_output=True, text=True)
    assert "Usage:" in res.stdout

def test_script_dry_run(tmp_path):
    out_dir = tmp_path / "billing"
    res = subprocess.run([
        "./scripts/validators/validate-real-billing-margin.sh",
        "--dry-run",
        "--output-dir", str(out_dir)
    ], capture_output=True, text=True)
    assert res.returncode == 0
    assert "Financial Calculation" in res.stdout
    assert "Admin sees margin: True" in res.stdout

def test_script_real_requires_env(tmp_path):
    out_dir = tmp_path / "billing"
    env = os.environ.copy()
    if "REAL_PROVIDER_VALIDATION_ENABLED" in env:
        del env["REAL_PROVIDER_VALIDATION_ENABLED"]
        
    res = subprocess.run([
        "./scripts/validators/validate-real-billing-margin.sh",
        "--real",
        "--output-dir", str(out_dir)
    ], capture_output=True, text=True, env=env)
    assert res.returncode != 0
    assert "REAL_PROVIDER_VALIDATION_ENABLED is not set to true" in res.stdout
