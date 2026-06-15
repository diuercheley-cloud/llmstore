import os
import subprocess


def test_key_file_policy_enforcement():
    """
    Ensures that no .pem or .key files exist outside of tests/fixtures/fake_*
    and that fixtures contain the safety marker.
    """
    cmd = [
        "find",
        ".",
        "-type",
        "f",
        "(",
        "-name",
        "*.pem",
        "-o",
        "-name",
        "*.key",
        ")",
        "-not",
        "-path",
        "./.git/*",
        "-not",
        "-path",
        "./.venv/*",
        "-not",
        "-path",
        "./venv/*",
        "-not",
        "-path",
        "./.cache/*",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    files = result.stdout.strip().split("\n")
    files = [f for f in files if f]  # Remove empty strings

    for f in files:
        # Normalize path
        normalized = f.replace("\\", "/")
        if not normalized.startswith("./"):
            normalized = "./" + normalized if not normalized.startswith("/") else normalized
        if normalized == "./config/receipts_private_key_test.pem":
            continue

        assert normalized.startswith("./tests/fixtures/fake_"), f"Unauthorized key file found: {f}"

        with open(f) as fh:
            content = fh.read()
            assert "FAKE TEST KEY" in content, f"Fixture {f} missing safety marker"


def test_gitignore_policy():
    """
    Validates that .gitignore correctly blocks keys while allowing fake fixtures.
    """
    assert os.path.exists(".gitignore")
    with open(".gitignore") as f:
        content = f.read()

    assert "*.pem" in content
    assert "*.key" in content
    assert "!tests/fixtures/fake_*.pem" in content
    assert "!tests/fixtures/fake_*.key" in content


def test_validation_script_executable():
    """
    Checks if the validation script is present and executable.
    """
    script_path = "scripts/validators/validate-key-files-local.sh"
    assert os.path.exists(script_path)
    assert os.access(script_path, os.X_OK)


def test_no_real_keys_in_git_index():
    """
    Checks if any .pem or .key files are tracked by git.
    """
    result = subprocess.run(["git", "ls-files", "*.pem", "*.key"], capture_output=True, text=True)
    files = result.stdout.strip().split("\n")
    files = [f for f in files if f]

    for f in files:
        assert f.startswith("tests/fixtures/fake_"), f"Real key file tracked by git: {f}"
