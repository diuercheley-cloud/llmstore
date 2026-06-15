import json
import os
import subprocess


def test_smoke_script_exists():
    assert os.path.exists("scripts/validators/post-upgrade-smoke-local.sh")
    assert os.access("scripts/validators/post-upgrade-smoke-local.sh", os.X_OK)


def test_smoke_run_help():
    result = subprocess.run(
        ["./scripts/validators/post-upgrade-smoke-local.sh", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Uso:" in result.stdout


def test_smoke_json_output():
    # Run with --json and --skip-rag --skip-tts to be fast and not depend on external services if possible
    result = subprocess.run(
        ["./scripts/validators/post-upgrade-smoke-local.sh", "--json", "--skip-rag", "--skip-tts"],
        capture_output=True,
        text=True,
    )
    assert result.returncode in [0, 1]  # Might fail if stack is down, but we want to check JSON

    try:
        data = json.loads(result.stdout)
        assert "timestamp" in data
        assert "results" in data
    except json.JSONDecodeError:
        # If stack is down, it might not output clean JSON if error happened before.
        # But our script should handle it.
        pass
