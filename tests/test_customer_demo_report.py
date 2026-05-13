import os
import json
import glob
import re


def _get_latest_report():
    reports = sorted(glob.glob("artifacts/customer-demo/*/customer-demo-report.json"))
    if not reports:
        return None
    return reports[-1]


def test_report_json_exists():
    report = _get_latest_report()
    assert report is not None, "Nenhum relatorio JSON encontrado em artifacts/customer-demo/"
    assert os.path.isfile(report)


def test_report_json_valid():
    report = _get_latest_report()
    with open(report) as f:
        data = json.load(f)
    assert isinstance(data, dict)


def test_report_has_required_keys():
    report = _get_latest_report()
    with open(report) as f:
        data = json.load(f)
    required = ["report_type", "version", "timestamp", "base_url", "mode", "status", "counts", "results"]
    for key in required:
        assert key in data, f"Chave obrigatoria '{key}' ausente no relatorio"


def test_report_counts_consistent():
    report = _get_latest_report()
    with open(report) as f:
        data = json.load(f)
    counts = data["counts"]
    results = data["results"]
    total_from_results = len(results)
    total_from_counts = counts["pass"] + counts.get("warn", 0) + counts.get("fail", 0)
    # Results may include items not counted in pass/warn/fail
    assert total_from_results >= total_from_counts


def test_report_no_secrets():
    report = _get_latest_report()
    with open(report) as f:
        content = f.read()
    # Check for potential secrets
    patterns = [
        r'sk-[a-zA-Z0-9]{20,}',
        r'ADMIN_TOKEN=[a-zA-Z0-9._-]{12,}',
        r'ghp_[a-zA-Z0-9]{36}',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            # Allow demo/safe patterns
            if match.startswith("sk-demo-") or match.startswith("sk-local-"):
                continue
            assert False, f"Possivel secret encontrado: {match[:20]}..."


def test_report_status_valid():
    report = _get_latest_report()
    with open(report) as f:
        data = json.load(f)
    assert data["status"] in (
        "CUSTOMER_DEMO_READY",
        "CUSTOMER_DEMO_READY_WITH_WARNINGS",
        "CUSTOMER_DEMO_FAILED"
    ), f"Status invalido: {data['status']}"


def test_report_md_exists():
    reports = sorted(glob.glob("artifacts/customer-demo/*/customer-demo-report.md"))
    assert len(reports) > 0, "Nenhum relatorio MD encontrado"


def test_report_md_has_content():
    reports = sorted(glob.glob("artifacts/customer-demo/*/customer-demo-report.md"))
    with open(reports[-1]) as f:
        content = f.read()
    assert "Customer Demo" in content
    assert "Status" in content
    assert "Resultados" in content or "Results" in content


def test_report_md_no_secrets():
    reports = sorted(glob.glob("artifacts/customer-demo/*/customer-demo-report.md"))
    with open(reports[-1]) as f:
        content = f.read()
    patterns = [
        r'sk-[a-zA-Z0-9]{20,}',
        r'ADMIN_TOKEN=[a-zA-Z0-9._-]{12,}',
        r'ghp_[a-zA-Z0-9]{36}',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            if match.startswith("sk-demo-") or match.startswith("sk-local-"):
                continue
            assert False, f"Possivel secret no relatorio MD: {match[:20]}..."
