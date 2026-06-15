import subprocess


def test_help_command():
    result = subprocess.run(
        ["./scripts/validators/validate-post-install-local.sh", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Usage:" in result.stdout


def test_script_execution():
    result = subprocess.run(
        [
            "./scripts/validators/validate-post-install-local.sh",
            "--base-url",
            "http://localhost:9999",
            "--output-dir",
            "artifacts/test-pytest-output",
            "--skip-rag",
            "--skip-tts",
        ],
        capture_output=True,
        text=True,
    )
    # Even if it fails due to no server, it should generate report and exit correctly
    assert result.returncode in [0, 1]
    assert (
        "artifacts/test-pytest-output" in result.stdout
        or "artifacts/test-pytest-output" in result.stderr
    )
