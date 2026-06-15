import json
from pathlib import Path


def test_production_readiness_ready_score():
    reports_dir = Path("artifacts/production-readiness")
    if not reports_dir.exists():
        return  # Skip if no report has been generated yet

    # Get latest report.json
    report_files = list(reports_dir.glob("*/report.json"))
    if not report_files:
        return

    latest_report = sorted(report_files, key=lambda p: p.stat().st_mtime)[-1]

    with open(latest_report) as f:
        data = json.load(f)

    assert data.get("score") == "READY", f"Score deveria ser READY, foi {data.get('score')}"
    assert data.get("totals", {}).get("critical_failures", 1) == 0, (
        "Não deveria haver critical failures"
    )
