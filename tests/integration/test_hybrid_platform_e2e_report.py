import json
import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
REPORT_SCRIPT = ROOT / "scripts" / "validate-hybrid-platform-report.sh"
ARTIFACTS_DIR = ROOT / "artifacts" / "hybrid-platform-e2e"


class TestHybridPlatformE2EReport:
    def _find_latest_report(self) -> Path | None:
        if not ARTIFACTS_DIR.exists():
            return None
        dirs = sorted(ARTIFACTS_DIR.iterdir())
        if not dirs:
            return None
        latest = dirs[-1]
        if not latest.is_dir():
            return None
        return latest

    def _get_report_json(self) -> dict | None:
        latest = self._find_latest_report()
        if latest is None:
            return None
        report_file = latest / "hybrid-e2e.json"
        if not report_file.exists():
            return None
        with open(report_file) as f:
            return json.load(f)

    def _get_report_md(self) -> str | None:
        latest = self._find_latest_report()
        if latest is None:
            return None
        report_file = latest / "hybrid-e2e.md"
        if not report_file.exists():
            return None
        return report_file.read_text()

    def test_report_validation_script_exists(self):
        assert REPORT_SCRIPT.exists(), f"Report script not found: {REPORT_SCRIPT}"

    def test_report_validation_script_executable(self):
        assert os.access(str(REPORT_SCRIPT), os.X_OK), (
            f"Report script not executable: {REPORT_SCRIPT}"
        )

    def test_report_validation_script_runs(self):
        result = subprocess.run(
            ["bash", str(REPORT_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        # Must not crash
        assert result.returncode in (0, 1), (
            f"Report script crashed: {result.returncode}\n"
            f"stdout: {result.stdout[:300]}\n"
            f"stderr: {result.stderr[:300]}"
        )

    def test_latest_report_dir_exists(self):
        latest = self._find_latest_report()
        if latest is None:
            pytest.skip("No report directories found")
        assert latest.is_dir()

    def test_latest_report_has_json(self):
        latest = self._find_latest_report()
        if latest is None:
            pytest.skip("No report directories found")
        assert (latest / "hybrid-e2e.json").exists(), f"hybrid-e2e.json not in {latest}"

    def test_latest_report_has_md(self):
        latest = self._find_latest_report()
        if latest is None:
            pytest.skip("No report directories found")
        assert (latest / "hybrid-e2e.md").exists(), f"hybrid-e2e.md not in {latest}"

    def test_report_json_is_valid(self):
        data = self._get_report_json()
        if data is None:
            pytest.skip("No report JSON found")
        assert isinstance(data, dict), "Report must be a dict"
        assert "timestamp" in data, "Missing timestamp"
        assert "platform" in data, "Missing platform"
        assert "summary" in data, "Missing summary"
        assert "results" in data, "Missing results"

    def test_report_json_summary_fields(self):
        data = self._get_report_json()
        if data is None:
            pytest.skip("No report JSON found")
        summary = data.get("summary", {})
        assert "passed" in summary, "Missing summary.passed"
        assert "failed" in summary, "Missing summary.failed"
        assert "warnings" in summary, "Missing summary.warnings"
        assert "total" in summary, "Missing summary.total"

    def test_report_json_results_have_required_fields(self):
        data = self._get_report_json()
        if data is None:
            pytest.skip("No report JSON found")
        for result in data.get("results", []):
            assert "step" in result, f"Result missing 'step': {result}"
            assert "status" in result, f"Result missing 'status': {result}"
            assert result["status"] in ("PASS", "FAIL", "WARN"), (
                f"Invalid status: {result['status']}"
            )

    def test_report_json_no_secrets(self):
        data = self._get_report_json()
        if data is None:
            pytest.skip("No report JSON found")
        text = json.dumps(data).lower()
        dangerous = re.findall(r"sk-[a-z0-9]{20,}", text)
        dangerous = [
            s for s in dangerous if "demo" not in s and "example" not in s and "test" not in s
        ]
        assert len(dangerous) == 0, f"Potential secrets found in report: {dangerous}"

    def test_report_md_has_status_line(self):
        md = self._get_report_md()
        if md is None:
            pytest.skip("No report MD found")
        assert "HYBRID_READY" in md or "HYBRID_FAILED" in md, "Report MD must contain status line"

    def test_report_md_mentions_providers(self):
        md = self._get_report_md()
        if md is None:
            pytest.skip("No report MD found")
        assert re.search(r"provider", md, re.IGNORECASE), "Report MD must mention providers"

    def test_report_md_mentions_billing(self):
        md = self._get_report_md()
        if md is None:
            pytest.skip("No report MD found")
        assert re.search(r"billing", md, re.IGNORECASE), "Report MD must mention billing"

    def test_report_md_mentions_wallet(self):
        md = self._get_report_md()
        if md is None:
            pytest.skip("No report MD found")
        assert re.search(r"wallet", md, re.IGNORECASE), "Report MD must mention wallet"

    def test_report_md_mentions_cache(self):
        md = self._get_report_md()
        if md is None:
            pytest.skip("No report MD found")
        assert re.search(r"cache", md, re.IGNORECASE), "Report MD must mention cache"

    def test_report_md_mentions_rag(self):
        md = self._get_report_md()
        if md is None:
            pytest.skip("No report MD found")
        assert re.search(r"rag", md, re.IGNORECASE), "Report MD must mention RAG"

    def test_report_md_mentions_pix_out_of_scope(self):
        md = self._get_report_md()
        if md is None:
            pytest.skip("No report MD found")
        assert "pix" in md.lower(), "Report MD must mention PIX is out of scope"

    def test_report_md_summary_table(self):
        md = self._get_report_md()
        if md is None:
            pytest.skip("No report MD found")
        assert "| Passed |" in md, "Report MD must have summary table"
        assert "| Failed |" in md, "Report MD must have summary table"
        assert "| Warnings |" in md, "Report MD must have summary table"
        assert "| Total |" in md, "Report MD must have summary table"

    def test_report_mentions_out_of_scope(self):
        data = self._get_report_json()
        if data is None:
            pytest.skip("No report JSON found")
        oos = data.get("out_of_scope", [])
        assert len(oos) > 0, "Report must list out-of-scope items"
        has_pix = any("pix" in item.lower() for item in oos)
        has_cloud = any("cloud" in item.lower() for item in oos)
        assert has_pix, "Out-of-scope must mention PIX is excluded"
        assert has_cloud, "Out-of-scope must mention cloud is excluded"

    def test_report_summary_totals_are_consistent(self):
        data = self._get_report_json()
        if data is None:
            pytest.skip("No report JSON found")
        summary = data.get("summary", {})
        passed = summary.get("passed", 0)
        failed = summary.get("failed", 0)
        warnings = summary.get("warnings", 0)
        total = summary.get("total", 0)
        assert passed + failed + warnings == total, (
            f"Summary totals inconsistent: {passed}+{failed}+{warnings} != {total}"
        )

    def test_report_json_platform_version(self):
        data = self._get_report_json()
        if data is None:
            pytest.skip("No report JSON found")
        platform = data.get("platform", "")
        assert "v1.8.0" in platform, f"Platform version mismatch: {platform}"
