from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_local_folder_is_ignored():
    gitignore_path = ROOT / ".gitignore"
    assert gitignore_path.exists()
    content = gitignore_path.read_text()
    assert ".local/" in content


def test_no_real_psp_integration_in_demo_scripts():
    scripts = [
        "scripts/dev/seed-demo-local.sh",
        "scripts/dev/reset-demo-local.sh",
        "scripts/validators/validate-demo-local.sh",
    ]
    forbidden_keywords = ["stripe", "mercadopago", "pagseguro", "live_key", "secret_key_real"]
    for script_path in scripts:
        full_path = ROOT / script_path
        content = full_path.read_text().lower()
        for key in forbidden_keywords:
            assert key not in content, f"Forbidden keyword '{key}' found in {script_path}"


def test_demo_mode_env_vars_in_example():
    env_example = ROOT / ".env.example"
    assert env_example.exists()
    content = env_example.read_text()
    assert "DEMO_MODE" in content
    assert "DEMO_CLIENT_EMAIL" in content
    assert "DEMO_PLAN" in content


def test_reset_script_requires_confirmation_or_flag():
    # If we run reset script without --yes and without interactive TTY, it should fail or wait.
    # We test it fails if it expects input.
    result = subprocess_run_with_timeout(["./scripts/dev/reset-demo-local.sh"], timeout=2)
    # If it didn't finish in 2s, it's likely waiting for confirmation, which is good for safety.
    assert result is None or result.returncode != 0


def subprocess_run_with_timeout(cmd, timeout=2):
    import subprocess

    try:
        return subprocess.run(cmd, cwd=ROOT, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None
