import os
import subprocess

SCRIPT = "scripts/dev/generate-sow-local.sh"


def test_generate_sow_basic():
    cmd = [
        "bash",
        SCRIPT,
        "--company-name",
        "Test Corp",
        "--project-name",
        "Local AI Project",
        "--plan",
        "Pro",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    assert "SOW generated successfully" in result.stdout

    # Extract output path
    output_path = None
    for line in result.stdout.splitlines():
        candidate = line.strip()
        if candidate.endswith("-sow.md"):
            output_path = candidate
            break

    assert output_path is not None, f"Could not find output path in:\n{result.stdout}"
    assert os.path.exists(output_path), f"Output file not found: {output_path}"

    # Verify content
    with open(output_path) as f:
        content = f.read()
    assert "Test Corp" in content
    assert "Local AI Project" in content or "projeto" in content
    assert "Local Appliance" in content
    assert "revisão jurídica" in content.lower()

    # Clean up
    os.remove(output_path)
    parent = os.path.dirname(output_path)
    os.rmdir(parent)


def test_generate_sow_with_custom_output():
    output_dir = "/tmp/test-sow-output"
    cmd = [
        "bash",
        SCRIPT,
        "--company-name",
        "Custom Corp",
        "--project-name",
        "Custom Project",
        "--plan",
        "Enterprise Local",
        "--output-dir",
        output_dir,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)

    # Find generated file
    output_path = None
    for line in result.stdout.splitlines():
        candidate = line.strip()
        if candidate.endswith("-sow.md"):
            output_path = candidate
            break

    assert output_path is not None
    assert output_dir in output_path

    # Clean up
    os.remove(output_path)
    os.rmdir(os.path.dirname(output_path))


def test_generate_sow_missing_args():
    cmd = ["bash", SCRIPT]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode != 0
    assert "Error" in result.stderr or "Error" in result.stdout


def test_generate_sow_help():
    cmd = ["bash", SCRIPT, "--help"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "Usage" in result.stdout
    assert "--company-name" in result.stdout
    assert "--project-name" in result.stdout
    assert "--plan" in result.stdout
    assert "--output-dir" in result.stdout


def test_generated_sow_has_legal_warning():
    cmd = [
        "bash",
        SCRIPT,
        "--company-name",
        "Legal Check Corp",
        "--project-name",
        "Legal Check Project",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)

    output_path = None
    for line in result.stdout.splitlines():
        candidate = line.strip()
        if candidate.endswith("-sow.md"):
            output_path = candidate
            break

    with open(output_path) as f:
        content = f.read()

    assert "AVISO JURÍDICO" in content
    assert "revisão jurídica" in content.lower()
    assert "não constitui aconselhamento jurídico" in content.lower()

    os.remove(output_path)
    os.rmdir(os.path.dirname(output_path))
