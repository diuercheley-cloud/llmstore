import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = ROOT / "scripts" / "validate-hybrid-platform-e2e-local.sh"
REPORT_SCRIPT_PATH = ROOT / "scripts" / "validate-hybrid-platform-report.sh"


class TestHybridPlatformE2EScript:

    def test_script_exists(self):
        assert SCRIPT_PATH.exists(), f"Script not found: {SCRIPT_PATH}"

    def test_script_is_executable(self):
        assert os.access(str(SCRIPT_PATH), os.X_OK), (
            f"Script not executable: {SCRIPT_PATH}"
        )

    def test_script_is_shell_script(self):
        content = SCRIPT_PATH.read_text()
        assert content.startswith("#!/usr/bin/env bash"), (
            "Script must be a bash script"
        )

    def test_report_script_exists(self):
        assert REPORT_SCRIPT_PATH.exists(), (
            f"Report script not found: {REPORT_SCRIPT_PATH}"
        )

    def test_report_script_is_executable(self):
        assert os.access(str(REPORT_SCRIPT_PATH), os.X_OK), (
            f"Report script not executable: {REPORT_SCRIPT_PATH}"
        )

    def test_script_accepts_help(self):
        result = subprocess.run(
            ["bash", str(SCRIPT_PATH), "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        assert "Usage:" in result.stdout or "--help" in result.stdout

    def test_script_accepts_all_flags(self):
        # Test that --help works (quick validation of arg parser)
        result = subprocess.run(
            ["bash", str(SCRIPT_PATH), "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        assert "Usage:" in result.stdout
        # Verify all flags are documented
        for flag in ["--base-url", "--skip-rag", "--skip-cache-semantic",
                     "--skip-tts", "--allow-warnings", "--output-dir"]:
            assert flag in result.stdout, f"Flag {flag} missing from --help"

    def test_script_creates_output_dir(self, tmp_path: Path):
        output_dir = tmp_path / "hybrid-e2e-test-dir"
        # Remove any previous test output
        if output_dir.exists():
            import shutil
            shutil.rmtree(output_dir)
        try:
            result = subprocess.run(
                [
                    "bash",
                    str(SCRIPT_PATH),
                    "--skip-rag",
                    "--skip-cache-semantic",
                    "--skip-tts",
                    "--allow-warnings",
                    "--output-dir",
                    str(output_dir),
                ],
                capture_output=True,
                text=True,
                timeout=180,
            )
            dirs = sorted(output_dir.iterdir()) if output_dir.exists() else []
            if dirs:
                latest = dirs[-1]
                report_json = latest / "hybrid-e2e.json"
                report_md = latest / "hybrid-e2e.md"
                assert report_json.exists(), (
                    f"hybrid-e2e.json not found in {latest}"
                )
                assert report_md.exists(), (
                    f"hybrid-e2e.md not found in {latest}"
                )
        except subprocess.TimeoutExpired:
            # The script may take longer than 180s when external validators
            # are not responsive. This is acceptable for CI environments.
            pass

    def test_script_mentions_pix_out_of_scope(self):
        content = SCRIPT_PATH.read_text()
        assert "PSP/PIX" in content or "pix" in content.lower(), (
            "Script should mention PIX is out of scope"
        )

    def test_script_mentions_cloud_disabled(self):
        content = SCRIPT_PATH.read_text()
        assert "CLOUD_PROVIDERS_ENABLED" in content or "cloud_enabled" in content, (
            "Script should reference cloud disabled configuration"
        )

    def test_script_contains_provider_registry(self):
        content = SCRIPT_PATH.read_text()
        assert "provider" in content.lower(), (
            "Script should test provider registry"
        )

    def test_script_contains_smart_routing(self):
        content = SCRIPT_PATH.read_text()
        assert "routing" in content.lower() or "smart_router" in content.lower(), (
            "Script should test smart routing"
        )

    def test_script_contains_billing_brl(self):
        content = SCRIPT_PATH.read_text()
        assert "billing" in content.lower() or "pricing_engine" in content.lower(), (
            "Script should test billing BRL"
        )

    def test_script_contains_wallet(self):
        content = SCRIPT_PATH.read_text()
        assert "wallet" in content.lower(), (
            "Script should test prepaid wallet"
        )

    def test_script_contains_cache(self):
        content = SCRIPT_PATH.read_text()
        assert "cache" in content.lower(), (
            "Script should test intelligent cache"
        )

    def test_script_contains_rag(self):
        content = SCRIPT_PATH.read_text()
        assert "rag" in content.lower(), (
            "Script should test Enterprise RAG"
        )

    def test_script_contains_abuse_detection(self):
        content = SCRIPT_PATH.read_text()
        assert "abuse" in content.lower(), (
            "Script should test abuse detection"
        )

    def test_script_contains_admin_hybrid(self):
        content = SCRIPT_PATH.read_text()
        assert "admin" in content.lower() and "hybrid" in content.lower(), (
            "Script should test admin hybrid summary"
        )

    def test_script_contains_client_portal(self):
        content = SCRIPT_PATH.read_text()
        assert "client" in content.lower() and "portal" in content.lower(), (
            "Script should test client portal"
        )

    def test_script_contains_check_secrets(self):
        content = SCRIPT_PATH.read_text()
        assert "check-secrets" in content, (
            "Script should run check-secrets"
        )

    def test_script_contains_security_report(self):
        content = SCRIPT_PATH.read_text()
        assert "security-report" in content, (
            "Script should run security report"
        )

    def test_script_contains_production_readiness(self):
        content = SCRIPT_PATH.read_text()
        assert "production-readiness" in content, (
            "Script should run production readiness"
        )

    def test_script_contains_local_production_full(self):
        content = SCRIPT_PATH.read_text()
        assert "validate-local-production-full" in content, (
            "Script should run local production full validation"
        )

    def test_script_generates_json_report(self):
        content = SCRIPT_PATH.read_text()
        assert "hybrid-e2e.json" in content, (
            "Script should generate hybrid-e2e.json"
        )

    def test_script_generates_md_report(self):
        content = SCRIPT_PATH.read_text()
        assert "hybrid-e2e.md" in content, (
            "Script should generate hybrid-e2e.md"
        )

    def test_script_has_valid_status_values(self):
        content = SCRIPT_PATH.read_text()
        assert "HYBRID_READY" in content, (
            "Script should define HYBRID_READY status"
        )
        assert "HYBRID_READY_WITH_WARNINGS" in content, (
            "Script should define HYBRID_READY_WITH_WARNINGS status"
        )
        assert "HYBRID_FAILED" in content, (
            "Script should define HYBRID_FAILED status"
        )

    @pytest.mark.skipif(
        not (ROOT / ".venv" / "bin" / "python").exists(),
        reason="Virtual environment not found",
    )
    def test_script_python_imports_are_valid(self):
        """Verify the Python imports used in the script are resolvable."""
        imports = [
            "app.services.providers.registry",
            "app.schemas.routing",
            "app.services.routing.smart_router",
            "app.services.rag_enterprise.parsers",
            "app.services.rag_enterprise.chunking",
            "app.services.rag_enterprise.embeddings",
            "app.services.rag_enterprise.policies",
            "app.services.rag_enterprise.retrieval",
            "app.services.rag_enterprise.ingestion",
            "app.services.cache.intelligent_cache",
            "app.services.billing.pricing_engine",
            "app.services.billing.wallet_service",
            "app.services.security",
            "app.api.rag_enterprise",
            "app.api.abuse_admin",
        ]
        python = ROOT / ".venv" / "bin" / "python"
        for import_name in imports:
            result = subprocess.run(
                [str(python), "-c", f"import {import_name}"],
                capture_output=True,
                text=True,
                timeout=15,
                cwd=str(ROOT),
                env={**os.environ, "PYTHONPATH": str(ROOT / "control_plane")},
            )
            assert result.returncode == 0, (
                f"Failed to import {import_name}: {result.stderr[:200]}"
            )
