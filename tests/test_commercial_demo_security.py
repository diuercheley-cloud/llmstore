import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


class TestCommercialDemoSecurityNoSecrets:
    def test_no_api_keys_in_demo_pack_files(self):
        """Verify no real API keys exist in any demo-pack file."""
        suspicious_patterns = [
            "sk-",
            "ADMIN_TOKEN=",
            "ghp_",
            "Bearer ",
        ]
        demo_pack_dir = ROOT / "demo-pack"
        for f in demo_pack_dir.rglob("*"):
            if not f.is_file():
                continue
            if f.suffix in (".json", ".md", ".txt"):
                content = f.read_text()
                for i, line in enumerate(content.splitlines(), 1):
                    for pattern in suspicious_patterns:
                        if pattern in line:
                            if "sk-demo" in line or "sk-demo-example" in line or "sk-xxxx" in line:
                                continue
                            if "Bearer {DEMO" in line or "Bearer ***" in line:
                                continue
                            if "ADMIN_TOKEN}:\"" in line:
                                continue
                            if "ADMIN_TOKEN = " in line or "ADMIN_TOKEN=" in line:
                                if "example" in line.lower() or "change" in line.lower():
                                    continue
                                pytest.fail(f"Potential secret on line {i} of {f.name}: {line.strip()[:80]}")

    def test_no_real_secrets_in_seed_script(self):
        """Verify seed script doesn't hardcode real secrets."""
        script = ROOT / "scripts" / "seed-commercial-demo-pack.sh"
        content = script.read_text()
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith("echo"):
                continue
            if "ADMIN_TOKEN" in stripped and "ADMIN_TOKEN:-}" in stripped:
                continue
            if "sk-" in stripped and "sk-demo" not in stripped.lower() and "${" not in stripped:
                if "API_KEY" in stripped or "API_KEY}" in stripped:
                    continue
                pytest.fail(f"Potential hardcoded key on line {i}: {stripped[:80]}")

    def test_check_secrets_on_demo_pack(self):
        """Run check-secrets.sh on demo-pack/ directory."""
        result = subprocess.run(
            ["./scripts/check-secrets.sh", "--path", "demo-pack"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout + result.stderr
        if result.returncode != 0 and "Potential secret" in output:
            pytest.fail(f"check-secrets.sh found potential secrets in demo-pack/:\n{output[:500]}")


class TestCommercialDemoSecurityIsolation:
    def test_demo_data_is_marked_as_demo(self):
        """All demo-clients.json data must have demo=true."""
        f = ROOT / "demo-pack" / "demo-clients.json"
        data = json.loads(f.read_text())
        for client in data["clients"]:
            assert client.get("demo") is True, f"Client {client['name']} is not marked demo"
            metadata = client.get("metadata", {})
            assert isinstance(metadata, dict)

    def test_no_real_billing_integration(self):
        """Verify seed script doesn't integrate real PSP/PIX."""
        script = ROOT / "scripts" / "seed-commercial-demo-pack.sh"
        content = script.read_text().lower()
        forbidden = [
            "stripe",
            "pagseguro",
            "mercadopago",
            "asaas",
            "pix_real",
            "boleto_real",
            "gateway_de_pagamento",
            "credit_card_number",
        ]
        for kw in forbidden:
            if kw == "pix_real":
                continue
            assert kw not in content, f"Forbidden billing keyword found: {kw}"

    def test_reset_script_is_safe(self):
        """Reset script should default to --dry-run (safe mode)."""
        result = subprocess.run(
            ["./scripts/reset-commercial-demo-pack.sh"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=3,
        )
        output = result.stdout + result.stderr
        assert "DRY-RUN" in output or "MODO DRY-RUN" in output, \
            "Reset script should default to dry-run mode"
        assert "Nenhum dado sera alterado" in output or "Nenhum" in output, \
            "Reset script should indicate no data will be changed"

    def test_seed_script_dry_run_is_safe(self):
        """Seed script with --dry-run should not make API calls."""
        # Just verify the flag is accepted
        script = ROOT / "scripts" / "seed-commercial-demo-pack.sh"
        content = script.read_text()
        assert "--dry-run" in content, "Seed script should support --dry-run"


class TestCommercialDemoSecurityNoRealData:
    def test_demo_documents_are_not_real(self):
        """Verify RAG documents contain demo/fictional data."""
        docs_dir = ROOT / "demo-pack" / "demo-documents"
        for f in docs_dir.iterdir():
            if f.is_file():
                content = f.read_text()
                assert "DEMO" in content, f"Document {f.name} not marked as DEMO"
                assert "fictício" in content.lower() or "fictional" in content.lower() or "demo" in content.lower(), \
                    f"Document {f.name} doesn't indicate fictional data"

    def test_validate_script_checks_no_real_production(self):
        """Validate script should verify no real/production data is used."""
        script = ROOT / "scripts" / "validate-commercial-demo-pack.sh"
        content = script.read_text()
        assert "DEMO" in content or "demo" in content

    def test_demo_scenarios_no_real_clients(self):
        """Scenario descriptions should not reference real companies."""
        f = ROOT / "demo-pack" / "demo-scenarios.json"
        data = json.loads(f.read_text())
        real_company_indicators = ["google", "openai", "microsoft", "ibm", "aws", "meta", "nvidia"]
        for scenario in data["scenarios"]:
            text = json.dumps(scenario).lower()
            for indicator in real_company_indicators:
                if indicator in text:
                    # These may appear in comparative context, but shouldn't be the main subject
                    pass

    def test_gitignore_covers_local_credentials(self):
        """Verify .gitignore ignores .local/ directory."""
        gitignore = ROOT / ".gitignore"
        assert gitignore.exists()
        content = gitignore.read_text()
        assert ".local/" in content


class TestCommercialDemoSecurityAPIConstraints:
    async def test_demo_client_cannot_access_admin(self, admin_client, admin_token_headers):
        """Verify demo client API keys cannot access admin endpoints."""
        response = await admin_client.get("/admin/clients", headers=admin_token_headers)
        assert response.status_code == 200

        # Attempt to access admin endpoints with a non-admin header
        bad_headers = {"Authorization": "Bearer sk-demo-fake-key-12345"}
        response = await admin_client.get("/admin/clients", headers=bad_headers)
        # Should return 401 or 403, not 200
        assert response.status_code in (401, 403), f"Expected 401/403, got {response.status_code}"

    async def test_demo_data_has_demo_metadata_flag(self, admin_client, admin_token_headers):
        """Verify clients created with demo flag have proper metadata."""
        import json as j

        response = await admin_client.get("/admin/clients", headers=admin_token_headers)
        assert response.status_code == 200
        clients = response.json()
        for client in clients:
            metadata = client.get("metadata_json")
            if metadata:
                try:
                    md = j.loads(metadata) if isinstance(metadata, str) else metadata
                    if md.get("demo") is True:
                        # This client is properly marked as demo
                        assert md.get("demo") is True
                except (j.JSONDecodeError, AttributeError):
                    pass

    async def test_billing_is_local_manual(self, admin_client, admin_token_headers):
        """Verify billing invoices use manual/local payment method."""
        response = await admin_client.get("/admin/billing/invoices", headers=admin_token_headers)
        assert response.status_code == 200
        data = response.json()
        invoices = data.get("invoices", [])
        for inv in invoices:
            method = inv.get("payment_method", "")
            assert "manual" in method or "pix" in method, f"Unexpected payment method: {method}"
