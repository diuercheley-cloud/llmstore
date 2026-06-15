import json
import os
import subprocess

SCRIPT = "scripts/validators/paid-implementation-checklist-local.sh"


def _extract_path(output: str, suffix: str) -> str | None:
    for line in output.splitlines():
        if ":" in line and suffix in line:
            return line.split(":", 1)[1].strip()
    return None


def test_generate_checklist_basic():
    cmd = [
        "bash",
        SCRIPT,
        "--company-name",
        "Test Client",
        "--operator-name",
        "Test Provider",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    assert "Implementation checklist generated successfully" in result.stdout

    md_path = _extract_path(result.stdout, "implementation-checklist.md")
    json_path = _extract_path(result.stdout, "implementation-checklist.json")

    assert md_path is not None, f"MD path not found in:\n{result.stdout}"
    assert json_path is not None
    assert os.path.exists(md_path)
    assert os.path.exists(json_path)

    with open(md_path) as f:
        content = f.read()
    assert "Test Client" in content
    assert "Test Provider" in content
    assert "NOT_STARTED" in content

    with open(json_path) as f:
        data = json.load(f)
    assert data["company_name"] == "Test Client"
    assert data["operator_name"] == "Test Provider"
    assert data["status"]["overall"] == "NOT_STARTED"
    assert "valid_statuses" in data
    assert data["psp_pix_disclaimer"] != ""

    os.remove(md_path)
    os.remove(json_path)
    os.rmdir(os.path.dirname(md_path))


def test_generate_checklist_custom_output():
    output_dir = "/tmp/test-pic-output"
    cmd = [
        "bash",
        SCRIPT,
        "--company-name",
        "Custom Client",
        "--operator-name",
        "Custom Provider",
        "--output-dir",
        output_dir,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)

    md_path = _extract_path(result.stdout, "implementation-checklist.md")
    json_path = _extract_path(result.stdout, "implementation-checklist.json")

    assert md_path is not None
    assert json_path is not None
    assert output_dir in md_path
    assert output_dir in json_path

    os.remove(md_path)
    os.remove(json_path)
    os.rmdir(os.path.dirname(md_path))


def test_generate_checklist_missing_args():
    cmd = ["bash", SCRIPT]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode != 0
    assert "Error" in result.stderr or "Error" in result.stdout

    cmd_missing = ["bash", SCRIPT, "--company-name", "Only Name"]
    result = subprocess.run(cmd_missing, capture_output=True, text=True)
    assert result.returncode != 0


def test_generate_checklist_help():
    cmd = ["bash", SCRIPT, "--help"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "Usage" in result.stdout
    assert "--company-name" in result.stdout
    assert "--operator-name" in result.stdout
    assert "--output-dir" in result.stdout


def test_json_valid_structure():
    cmd = [
        "bash",
        SCRIPT,
        "--company-name",
        "JSON Test",
        "--operator-name",
        "JSON Validator",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)

    json_path = _extract_path(result.stdout, "implementation-checklist.json")

    with open(json_path) as f:
        data = json.load(f)

    assert "template" in data
    assert "company_name" in data
    assert "operator_name" in data
    assert "generated_at" in data
    assert "status" in data
    assert "sections" in data["status"]
    assert "valid_statuses" in data
    assert "psp_pix_disclaimer" in data
    assert "legal_disclaimer" in data

    os.remove(json_path)
    os.remove(json_path.replace(".json", ".md"))
    os.rmdir(os.path.dirname(json_path))
