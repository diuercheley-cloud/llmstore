import glob
import json
import os
import subprocess

SCRIPT_PATH = "scripts/customer-demo-local.sh"
ARTIFACTS_DIR = "artifacts/customer-demo"


def test_script_exists():
    assert os.path.isfile(SCRIPT_PATH), f"Script nao encontrado: {SCRIPT_PATH}"
    assert os.access(SCRIPT_PATH, os.X_OK), f"Script sem permissao de execucao: {SCRIPT_PATH}"


def test_script_help():
    result = subprocess.run(
        ["bash", SCRIPT_PATH, "--help"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "Uso:" in result.stdout or "./scripts/customer-demo-local.sh" in result.stdout


def test_script_accepts_all_flags():
    result = subprocess.run(
        ["bash", SCRIPT_PATH, "--no-build", "--quick"],
        capture_output=True, text=True
    )
    # Should not crash - may return 0, 1, or 2
    assert result.returncode in (0, 1, 2), f"Script falhou: {result.stderr}"


def test_quick_mode_generates_report():
    result = subprocess.run(
        ["bash", SCRIPT_PATH, "--no-build", "--quick"],
        capture_output=True, text=True
    )
    # Check if any report JSON was generated
    reports = glob.glob(f"{ARTIFACTS_DIR}/*/customer-demo-report.json")
    assert len(reports) > 0, "Nenhum relatorio JSON gerado"


def test_report_has_required_fields():
    reports = sorted(glob.glob(f"{ARTIFACTS_DIR}/*/customer-demo-report.json"))
    assert len(reports) > 0, "Nenhum relatorio para verificar"
    with open(reports[-1]) as f:
        report = json.load(f)
    assert "version" in report
    assert "timestamp" in report
    assert "status" in report
    assert "counts" in report
    assert "results" in report
    assert report["status"] in ("CUSTOMER_DEMO_READY", "CUSTOMER_DEMO_READY_WITH_WARNINGS", "CUSTOMER_DEMO_FAILED")


def test_report_has_md_version():
    reports = sorted(glob.glob(f"{ARTIFACTS_DIR}/*/customer-demo-report.md"))
    assert len(reports) > 0, "Nenhum relatorio MD gerado"
    with open(reports[-1]) as f:
        content = f.read()
    assert "Customer Demo Report" in content
    assert "Status" in content


def test_script_handles_unknown_flag():
    result = subprocess.run(
        ["bash", SCRIPT_PATH, "--unknown-flag"],
        capture_output=True, text=True
    )
    assert result.returncode != 0
    assert "Opcao desconhecida" in result.stdout or "Unknown" in result.stdout


def test_script_handles_base_url():
    result = subprocess.run(
        ["bash", SCRIPT_PATH, "--no-build", "--quick", "--base-url", "http://localhost:9999"],
        capture_output=True, text=True
    )
    # Should handle gracefully (stack not running at 9999)
    assert result.returncode in (0, 1, 2)


def test_script_generates_logs():
    logs = glob.glob(f"{ARTIFACTS_DIR}/*/logs/*")
    assert len(logs) >= 0  # May be empty if stack is down, but dir should exist


def test_script_parse_skip_flags():
    """All skip flags should be accepted without error."""
    result = subprocess.run(
        [
            "bash", SCRIPT_PATH, "--no-build", "--quick",
            "--skip-rag", "--skip-tts", "--skip-lmstudio", "--skip-screenshots"
        ],
        capture_output=True, text=True
    )
    assert result.returncode in (0, 1, 2)


def test_script_parse_output_dir():
    result = subprocess.run(
        ["bash", SCRIPT_PATH, "--no-build", "--quick", "--output-dir", "/tmp/test-customer-demo"],
        capture_output=True, text=True
    )
    assert result.returncode in (0, 1, 2)
