import json
import os
import subprocess

SCRIPT = "scripts/validators/generate-client-monthly-report.sh"


def _extract_path(output: str, suffix: str) -> str | None:
    for line in output.splitlines():
        if ":" in line and suffix in line:
            return line.split(":", 1)[1].strip()
    return None


def test_generate_report_basic():
    cmd = [
        "bash",
        SCRIPT,
        "--client-id",
        "00000000-0000-0000-0000-000000000000",
        "--email",
        "test@example.local",
        "--month",
        "2026-05",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    assert "Monthly report generated successfully" in result.stdout

    md_path = _extract_path(result.stdout, "monthly-report.md")
    json_path = _extract_path(result.stdout, "monthly-report.json")

    assert md_path is not None, f"MD path not found in:\n{result.stdout}"
    assert json_path is not None
    assert os.path.exists(md_path)
    assert os.path.exists(json_path)

    with open(md_path) as f:
        content = f.read()
    assert "test@example.local" in content or "test" in content.lower()
    assert "Relatório Mensal" in content
    assert "2026-05" in content

    with open(json_path) as f:
        data = json.load(f)
    assert data["period"]["month"] == "2026-05"
    assert "usage" in data
    assert "billing" in data

    os.remove(md_path)
    os.remove(json_path)
    os.rmdir(os.path.dirname(md_path))


def test_generate_report_with_technical_details():
    cmd = [
        "bash",
        SCRIPT,
        "--email",
        "tech@example.local",
        "--month",
        "2026-06",
        "--include-technical-details",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)

    json_path = _extract_path(result.stdout, "monthly-report.json")
    assert json_path is not None

    with open(json_path) as f:
        data = json.load(f)
    assert data["period"]["month"] == "2026-06"
    assert data["period"]["year"] == 2026

    os.remove(json_path)
    md_path = json_path.replace(".json", ".md")
    if os.path.exists(md_path):
        os.remove(md_path)
    os.rmdir(os.path.dirname(json_path))


def test_generate_report_custom_output():
    output_dir = "/tmp/test-monthly-report"
    cmd = [
        "bash",
        SCRIPT,
        "--email",
        "custom@example.local",
        "--month",
        "2026-07",
        "--output-dir",
        output_dir,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)

    json_path = _extract_path(result.stdout, "monthly-report.json")
    assert json_path is not None
    assert output_dir in json_path

    os.remove(json_path)
    md_path = json_path.replace(".json", ".md")
    if os.path.exists(md_path):
        os.remove(md_path)
    os.rmdir(os.path.dirname(json_path))


def test_generate_report_missing_month():
    cmd = ["bash", SCRIPT, "--email", "test@example.local"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode != 0
    assert "Error" in result.stderr or "Error" in result.stdout


def test_generate_report_invalid_month():
    cmd = [
        "bash",
        SCRIPT,
        "--email",
        "test@example.local",
        "--month",
        "2026-13",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode != 0


def test_generate_report_help():
    cmd = ["bash", SCRIPT, "--help"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "Usage" in result.stdout
    assert "--client-id" in result.stdout
    assert "--email" in result.stdout
    assert "--month" in result.stdout
    assert "--output-dir" in result.stdout
    assert "--include-technical-details" in result.stdout


def test_json_has_required_fields():
    cmd = [
        "bash",
        SCRIPT,
        "--email",
        "fields@example.local",
        "--month",
        "2026-08",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)

    json_path = _extract_path(result.stdout, "monthly-report.json")
    with open(json_path) as f:
        data = json.load(f)

    required_fields = [
        "report_version",
        "generated_at",
        "generated_date",
        "client",
        "period",
        "usage",
        "billing",
        "recommendations",
    ]
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"

    usage_fields = [
        "chat_tokens",
        "requests",
        "responses",
        "embeddings_requests",
        "embeddings_tokens",
        "rag_queries",
        "rag_documents",
        "tts_chars",
        "errors",
        "rate_limit_events",
        "avg_latency_ms",
    ]
    for field in usage_fields:
        assert field in data["usage"], f"Missing usage field: {field}"

    billing_fields = ["total_billed", "total_paid", "total_pending", "payment_status"]
    for field in billing_fields:
        assert field in data["billing"], f"Missing billing field: {field}"

    os.remove(json_path)
    md_path = json_path.replace(".json", ".md")
    if os.path.exists(md_path):
        os.remove(md_path)
    os.rmdir(os.path.dirname(json_path))


def test_markdown_contains_required_sections():
    cmd = [
        "bash",
        SCRIPT,
        "--email",
        "sections@example.local",
        "--month",
        "2026-09",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)

    md_path = _extract_path(result.stdout, "monthly-report.md")
    with open(md_path) as f:
        content = f.read()

    required_sections = [
        "Resumo de Consumo",
        "Faturamento Local",
        "Recomendações",
        "Upgrade / Downgrade Sugerido",
        "Limitações",
    ]
    for section in required_sections:
        assert section in content, f"Missing section: {section}"

    os.remove(md_path)
    json_path = md_path.replace(".md", ".json")
    if os.path.exists(json_path):
        os.remove(json_path)
    os.rmdir(os.path.dirname(md_path))
