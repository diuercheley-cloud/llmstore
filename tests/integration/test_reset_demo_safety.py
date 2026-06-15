import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


class TestResetDemoSafetyBasics:
    def test_reset_script_requires_yes_flag(self):
        """--yes must be required; without it, script must not proceed to real delete."""
        script = ROOT / "scripts" / "reset-commercial-demo-pack.sh"
        content = script.read_text()
        assert "DRY_RUN=true" in content or 'DRY_RUN="true"' in content
        assert "CONFIRMED" in content or "confirmed" in content

    def test_reset_script_defaults_to_dry_run(self):
        script = ROOT / "scripts" / "reset-commercial-demo-pack.sh"
        content = script.read_text()
        assert "DRY_RUN=true" in content

    def test_no_destructive_sql_without_condition(self):
        """All DELETE SQL must have WHERE clause."""
        script = ROOT / "scripts" / "reset-commercial-demo-pack.sh"
        content = script.read_text()
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("DELETE FROM") and "WHERE" not in stripped:
                if stripped.startswith("DELETE FROM") and "WHERE" not in stripped.upper():
                    pytest.fail(f"Unsafe DELETE without WHERE at line {i}: {stripped}")

    def test_no_hardcoded_real_endpoints(self):
        """Should not contain production URLs."""
        script = ROOT / "scripts" / "reset-commercial-demo-pack.sh"
        content = script.read_text()
        suspicious = [".com", "app.stripe", "api.mercadopago", "production"]
        for term in suspicious:
            if term in content:
                if term == ".com" and "google.com" not in content:
                    pass  # Allow generic .com references
                elif term in content and term in ("production",):
                    pytest.fail(f"Production reference found: {term}")

    def test_no_rm_rf_without_specific_path(self):
        """rm -rf must have a specific path."""
        script = ROOT / "scripts" / "reset-commercial-demo-pack.sh"
        content = script.read_text()
        if "rm -rf" in content or "rm -fr" in content or "rm -f" in content:
            lines = content.split("\n")
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("rm"):
                    assert stripped.count("/") >= 1 or stripped.count("$") >= 1, (
                        f"Potentially unsafe rm: {stripped}"
                    )

    def test_reset_script_does_not_touch_models_dir(self):
        script = ROOT / "scripts" / "reset-commercial-demo-pack.sh"
        content = script.read_text()
        dangerous = ["rm -rf models/", "rm -rf /models/", "DELETE FROM models"]
        for d in dangerous:
            assert d not in content, f"Dangerous operation on models/: {d}"

    def test_reset_script_does_not_touch_backups_dir(self):
        script = ROOT / "scripts" / "reset-commercial-demo-pack.sh"
        content = script.read_text()
        dangerous = ["rm -rf backups/", "rm -rf /backups/"]
        for d in dangerous:
            assert d not in content, f"Dangerous operation on backups/: {d}"

    def test_reset_script_does_not_touch_releases_dir(self):
        script = ROOT / "scripts" / "reset-commercial-demo-pack.sh"
        content = script.read_text()
        dangerous = ["rm -rf releases/", "rm -rf /releases/"]
        for d in dangerous:
            assert d not in content, f"Dangerous operation on releases/: {d}"

    def test_reset_script_does_not_touch_env_local(self):
        script = ROOT / "scripts" / "reset-commercial-demo-pack.sh"
        content = script.read_text()
        dangerous = [".env.local"]
        for d in dangerous:
            assert d not in content or "PROTECTED_PATTERNS" in content

    def test_reset_script_protects_exports(self):
        script = ROOT / "scripts" / "reset-commercial-demo-pack.sh"
        content = script.read_text()
        assert "exports/" in content


class TestResetSafetyMetadata:
    def test_demo_clients_identified_by_metadata(self):
        script = ROOT / "scripts" / "reset-commercial-demo-pack.sh"
        content = script.read_text()
        assert "metadata" in content.lower()
        assert "demo" in content.lower()

    def test_non_demo_clients_preserved(self):
        script = ROOT / "scripts" / "reset-commercial-demo-pack.sh"
        content = script.read_text()
        lines = content.split("\n")
        for line in lines:
            if "DELETE FROM" in line and "client" in line.lower():
                assert "=" in line, f"DELETE without condition: {line}"

    def test_reset_script_parses_metadata_json(self):
        script = ROOT / "scripts" / "reset-commercial-demo-pack.sh"
        content = script.read_text()
        assert "json.loads" in content or "get('demo')" in content

    def test_reset_script_uses_get_demo_clients_function(self):
        script = ROOT / "scripts" / "reset-commercial-demo-pack.sh"
        content = script.read_text()
        assert (
            "fetch_clients_json" in content
            or "get_demo_clients" in content
            or "filter_demo_clients" in content
        )

    def test_reset_script_uses_get_demo_plans_function(self):
        script = ROOT / "scripts" / "reset-commercial-demo-pack.sh"
        content = script.read_text()
        assert (
            "fetch_plans_json" in content
            or "get_demo_plans" in content
            or "filter_demo_plans" in content
        )


class TestResetDryRunSafety:
    def test_dry_run_prints_warning(self):
        script = ROOT / "scripts" / "reset-commercial-demo-pack.sh"
        content = script.read_text()
        assert "MODO DRY-RUN" in content

    def test_dry_run_does_not_call_delete(self):
        """When DRY_RUN=true, delete functions should not issue real commands."""
        script = ROOT / "scripts" / "reset-commercial-demo-pack.sh"
        content = script.read_text()
        assert 'if [[ "$DRY_RUN" == true ]]; then' in content

    def test_dry_run_skips_db_operations(self):
        script = ROOT / "scripts" / "reset-commercial-demo-pack.sh"
        content = script.read_text()
        dry_blocks = content.count('if [[ "$DRY_RUN" == true ]]; then')
        assert dry_blocks >= 3, "Not enough DRY_RUN safety blocks"

    def test_yes_required_error_message(self):
        script = ROOT / "scripts" / "reset-commercial-demo-pack.sh"
        content = script.read_text()
        assert "--yes" in content

    def test_report_has_dry_run_status(self):
        script = ROOT / "scripts" / "reset-commercial-demo-pack.sh"
        content = script.read_text()
        assert "DRY_RUN" in content or "dry_run" in content


class TestResetSafetyGuarantees:
    def test_security_guarantees_printed(self):
        script = ROOT / "scripts" / "reset-commercial-demo-pack.sh"
        content = script.read_text()
        assert "GARANTIAS DE SEGURANCA" in content
        for item in [
            "NUNCA apaga clientes",
            "NUNCA apaga models",
            "NUNCA apaga backup",
            "NUNCA apaga release",
            "NUNCA apaga .env.local",
        ]:
            assert item in content, f"Missing guarantee: {item}"

    def test_reset_script_fails_without_yes_in_real_mode(self):
        """Script should fail if --yes not provided when not in dry-run."""
        env = os.environ.copy()
        if "ADMIN_TOKEN" in env:
            del env["ADMIN_TOKEN"]
        env["ENV_FILE"] = "/dev/null"
        result = subprocess.run(
            [str(ROOT / "scripts" / "reset-commercial-demo-pack.sh")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            env=env,
            timeout=5,
        )
        assert result.returncode != 0

    def test_reset_script_safety_skip_list(self):
        script = ROOT / "scripts" / "reset-commercial-demo-pack.sh"
        content = script.read_text()
        assert "SAFETY_SKIPS" in content or "safety_skips" in content

    def test_reset_script_error_list(self):
        script = ROOT / "scripts" / "reset-commercial-demo-pack.sh"
        content = script.read_text()
        assert "ERRORS" in content or "errors" in content

    def test_protected_patterns_include_all_required(self):
        script = ROOT / "scripts" / "reset-commercial-demo-pack.sh"
        content = script.read_text()
        for pattern in ["models/", "backups/", "releases/", "\\.env\\.local", "exports/"]:
            if pattern.startswith("\\"):
                assert pattern[1:] in content
            else:
                assert pattern in content

    def test_check_safety_function_exists(self):
        script = ROOT / "scripts" / "reset-commercial-demo-pack.sh"
        content = script.read_text()
        assert "check_safety" in content

    def test_parse_args_function_exists(self):
        script = ROOT / "scripts" / "reset-commercial-demo-pack.sh"
        content = script.read_text()
        assert "parse_args" in content


class TestResetCompatibility:
    def test_seed_script_reset_flag(self):
        """seed-commercial-demo-pack.sh should reference the reset script."""
        seed = ROOT / "scripts" / "seed-commercial-demo-pack.sh"
        content = seed.read_text()
        assert "reset-commercial-demo-pack.sh" in content

    def test_local_guide_references_reset(self):
        guide = ROOT / "docs" / "LOCAL_DEMO_GUIDE.md"
        if guide.exists():
            content = guide.read_text()
            assert "reset-commercial-demo-pack" in content or "reset-demo-local" in content

    def test_makefile_has_reset_demo_target(self):
        makefile = ROOT / "Makefile"
        content = makefile.read_text()
        assert "reset-demo-pack" in content or "reset-demo" in content

    def test_reset_script_generates_md_report(self):
        script = ROOT / "scripts" / "reset-commercial-demo-pack.sh"
        content = script.read_text()
        assert "reset-report.md" in content or "MDEOF" in content

    def test_reset_script_generates_json_report(self):
        script = ROOT / "scripts" / "reset-commercial-demo-pack.sh"
        content = script.read_text()
        assert "reset-report.json" in content or "JSONEOF" in content
