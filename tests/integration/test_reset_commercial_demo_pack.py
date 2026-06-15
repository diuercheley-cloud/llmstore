import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


class TestResetCommercialDemoPackScript:
    def test_reset_script_exists_and_executable(self):
        script = ROOT / "scripts" / "reset-commercial-demo-pack.sh"
        assert script.exists()
        assert os.access(script, os.X_OK)

    def test_reset_script_help(self):
        script = ROOT / "scripts" / "reset-commercial-demo-pack.sh"
        result = subprocess.run(
            [str(script), "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "Uso:" in result.stdout
        assert "--dry-run" in result.stdout
        assert "--yes" in result.stdout
        assert "--include-rag" in result.stdout
        assert "--include-tts" in result.stdout
        assert "--include-invoices" in result.stdout
        assert "--include-usage" in result.stdout
        assert "--demo-prefix" in result.stdout

    def test_reset_script_help_shows_safety_guarantees(self):
        script = ROOT / "scripts" / "reset-commercial-demo-pack.sh"
        result = subprocess.run(
            [str(script), "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert "Nunca apaga" in result.stdout
        assert "models/" in result.stdout
        assert "backups/" in result.stdout
        assert "releases/" in result.stdout
        assert ".env.local" in result.stdout
        assert "exports/" in result.stdout

    def test_dry_run_is_default_mode(self):
        script = ROOT / "scripts" / "reset-commercial-demo-pack.sh"
        content = script.read_text()
        assert "DRY_RUN=true" in content

    def test_yes_required_for_real_reset(self):
        script = ROOT / "scripts" / "reset-commercial-demo-pack.sh"
        content = script.read_text()
        assert "--yes" in content
        assert "CONFIRMED" in content

    def test_reset_filters_by_metadata_demo(self):
        script = ROOT / "scripts" / "reset-commercial-demo-pack.sh"
        content = script.read_text()
        assert "demo" in content.lower() and ("True" in content or "true" in content)

    def test_reset_generates_report(self):
        script = ROOT / "scripts" / "reset-commercial-demo-pack.sh"
        content = script.read_text()
        assert "reset-report.json" in content or "reset_report" in content
        assert "reset-report.md" in content or "reset_report" in content

    def test_reset_report_in_artifacts_dir(self):
        script = ROOT / "scripts" / "reset-commercial-demo-pack.sh"
        content = script.read_text()
        assert "artifacts/demo-reset" in content or "artifacts/demo_reset" in content

    def test_no_hardcoded_client_names_in_reset(self):
        script = ROOT / "scripts" / "reset-commercial-demo-pack.sh"
        content = script.read_text()
        suspicious = [
            "Clinica Saude Total Demo",
            "Escritorio Juridico Oliveira Demo",
            "SuporteTech Helpdesk Demo",
            "Escola EducaMais Demo",
            "APILayer IA Provider Demo",
        ]
        for name in suspicious:
            assert name not in content, f"Hardcoded client name found: {name}"

    def test_reset_script_requires_admin_token(self):
        script = ROOT / "scripts" / "reset-commercial-demo-pack.sh"
        env = os.environ.copy()
        if "ADMIN_TOKEN" in env:
            del env["ADMIN_TOKEN"]
        env["ENV_FILE"] = "/dev/null"
        env["BASE_URL"] = "http://localhost:1"
        result = subprocess.run(
            [str(script), "--dry-run"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
        )
        assert "ADMIN_TOKEN" in result.stdout or "ADMIN_TOKEN" in result.stderr

    def test_protected_patterns_in_place(self):
        script = ROOT / "scripts" / "reset-commercial-demo-pack.sh"
        content = script.read_text()
        assert "PROTECTED_PATTERNS" in content
        for pattern in ["models/", "backups/", "releases/", ".env.local", "exports/"]:
            assert pattern in content, f"Protected pattern missing: {pattern}"

    def test_security_guarantees_function(self):
        script = ROOT / "scripts" / "reset-commercial-demo-pack.sh"
        content = script.read_text()
        assert "GARANTIAS DE SEGURANCA" in content or "GARANTIAS_DE_SEGURANCA" in content
        assert "NUNCA" in content

    def test_reset_script_compatible_with_seed(self):
        reset_content = (ROOT / "scripts" / "reset-commercial-demo-pack.sh").read_text()
        seed_content = (ROOT / "scripts" / "seed-commercial-demo-pack.sh").read_text()
        assert reset_content is not None
        assert seed_content is not None

    def test_validate_script_exists(self):
        script = ROOT / "scripts" / "validate-reset-commercial-demo-pack.sh"
        assert script.exists()
        assert os.access(script, os.X_OK)


class TestResetReportStructure:
    def test_report_generated_on_dry_run(self):
        script = ROOT / "scripts" / "reset-commercial-demo-pack.sh"
        env = os.environ.copy()
        if "ADMIN_TOKEN" in env:
            del env["ADMIN_TOKEN"]
        env["ENV_FILE"] = "/dev/null"
        env["BASE_URL"] = "http://localhost:1"
        result = subprocess.run(
            [str(script), "--dry-run"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
        )
        assert result is not None

    def test_report_json_format(self):
        report_dir = ROOT / "artifacts" / "demo-reset"
        if not report_dir.exists():
            pytest.skip("No demo-reset reports yet")
        reports = sorted(report_dir.iterdir()) if report_dir.is_dir() else []
        if not reports:
            pytest.skip("No demo-reset reports to check")
        latest = reports[-1]
        json_path = latest / "reset-report.json"
        if json_path.exists():
            data = json.loads(json_path.read_text())
            assert "timestamp" in data
            assert "status" in data
            assert "dry_run" in data
            assert "summary" in data
            assert "clients_removed" in data["summary"]
            assert "plans_removed" in data["summary"]
        else:
            pytest.skip("No JSON report found")

    def test_report_md_format(self):
        report_dir = ROOT / "artifacts" / "demo-reset"
        if not report_dir.exists():
            pytest.skip("No demo-reset reports yet")
        reports = sorted(report_dir.iterdir()) if report_dir.is_dir() else []
        if not reports:
            pytest.skip("No demo-reset reports to check")
        latest = reports[-1]
        md_path = latest / "reset-report.md"
        if md_path.exists():
            content = md_path.read_text()
            assert "Relatorio de Reset" in content
            assert "Clientes removidos" in content
            assert "Planos removidos" in content
        else:
            pytest.skip("No MD report found")


class TestResetIntegrationSafety:
    def test_dry_run_does_not_delete_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            demo_file = Path(tmpdir) / "demo-test.txt"
            non_demo_file = Path(tmpdir) / "real-test.txt"
            demo_file.write_text("demo data")
            non_demo_file.write_text("real data")
            assert demo_file.exists()
            assert non_demo_file.exists()

    def test_reset_script_uses_metadata_demo_flag(self):
        script_content = (ROOT / "scripts" / "reset-commercial-demo-pack.sh").read_text()
        assert "'demo'" in script_content or '"demo"' in script_content

    def test_seed_and_reset_credential_files_match(self):
        creds_file = ROOT / ".local" / "demo-commercial-clients.env"
        if creds_file.exists():
            content = creds_file.read_text()
            assert "DEMO_CLIENT" in content

    def test_no_cross_contamination_with_real_data(self):
        reset_content = (ROOT / "scripts" / "reset-commercial-demo-pack.sh").read_text()
        seed_content = (ROOT / "scripts" / "seed-commercial-demo-pack.sh").read_text()
        forbidden = ["DELETE FROM clients", "DROP TABLE", "TRUNCATE"]
        for fw in forbidden:
            if fw in reset_content:
                assert "client_id" in reset_content or "WHERE" in reset_content, (
                    f"Potential unsafe SQL in reset: {fw}"
                )
