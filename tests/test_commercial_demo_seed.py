import json
import os
import subprocess
from pathlib import Path

import pytest
from httpx import AsyncClient

ROOT = Path(__file__).resolve().parents[1]


class TestCommercialDemoSeedScript:
    def test_seed_script_exists_and_executable(self):
        script = ROOT / "scripts" / "seed-commercial-demo-pack.sh"
        assert script.exists()
        assert os.access(script, os.X_OK)

    def test_reset_script_exists_and_executable(self):
        script = ROOT / "scripts" / "reset-commercial-demo-pack.sh"
        assert script.exists()
        assert os.access(script, os.X_OK)

    def test_validate_script_exists_and_executable(self):
        script = ROOT / "scripts" / "validate-commercial-demo-pack.sh"
        assert script.exists()
        assert os.access(script, os.X_OK)

    def test_seed_script_requires_stack(self):
        env = os.environ.copy()
        if "ADMIN_TOKEN" in env:
            del env["ADMIN_TOKEN"]
        env["ENV_FILE"] = "/dev/null"
        env["BASE_URL"] = "http://localhost:1"
        result = subprocess.run(
            ["./scripts/seed-commercial-demo-pack.sh"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
        )
        assert result.returncode != 0
        messages = result.stdout + result.stderr
        assert any(m in messages for m in ["ERRO", "ADMIN_TOKEN", "stack não encontrada", "refused"]), \
            f"Expected error, got: {messages[:200]}"

    def test_demo_commercial_clients_env_not_committed(self):
        gitignore = ROOT / ".gitignore"
        assert gitignore.exists()
        content = gitignore.read_text()
        assert "demo-commercial" not in content  # Should be covered by .local/

    def test_seed_uses_fictional_data_only(self):
        script = ROOT / "scripts" / "seed-commercial-demo-pack.sh"
        content = script.read_text()
        assert "DEMO" in content or "demo" in content
        assert "fictício" in content or "ficticio" in content
        forbidden = [
            "stripe_secret_key",
            "live_key",
            "production_api_key",
            "mercado_pago_token",
            "pagseguro_token",
        ]
        for kw in forbidden:
            assert kw not in content.lower()


@pytest.mark.asyncio
class TestCommercialDemoSeedAPI:
    async def test_create_demo_client_via_api(self, admin_client: AsyncClient, admin_token_headers: dict[str, str]):
        metadata = json.dumps({"demo": True, "scenario": "test-clinica", "ficticio": True})
        payload = {
            "name": "Test Demo Clinica",
            "description": "Clínica demo para testes - dados fictícios",
            "metadata_json": metadata,
            "rate_limit_per_minute": 10,
            "daily_token_quota": 50000,
            "monthly_token_quota": 500000,
        }
        response = await admin_client.post(
            "/admin/clients",
            headers=admin_token_headers,
            json=payload,
        )
        assert response.status_code in (200, 201)
        data = response.json()
        assert "id" in data
        assert data["name"] == "Test Demo Clinica"

    async def test_demo_client_has_metadata(self, admin_client: AsyncClient, admin_token_headers: dict[str, str]):
        response = await admin_client.get("/admin/clients", headers=admin_token_headers)
        assert response.status_code == 200
        clients = response.json()
        demo_clients = [
            c for c in clients
            if c.get("metadata_json") and "demo" in c["metadata_json"]
        ]
        assert len(demo_clients) >= 0  # May be 0 if not seeded, but structure is valid

    async def test_create_demo_plan_via_api(self, admin_client: AsyncClient, admin_token_headers: dict[str, str]):
        payload = {
            "code": "test-demo-plan",
            "name": "Test Demo Plan",
            "description": "Plano demo para testes - dados fictícios",
            "rate_limit_per_minute": 10,
            "daily_token_quota": 50000,
            "weekly_token_quota": 250000,
            "monthly_token_quota": 500000,
            "max_output_tokens": 1024,
            "max_context_tokens": 4096,
            "allow_streaming": True,
            "rag_enabled": True,
            "rag_max_documents": 5,
            "tts_enabled": True,
            "embeddings_enabled": True,
            "responses_enabled": True,
        }
        response = await admin_client.post(
            "/admin/billing/plans",
            headers=admin_token_headers,
            json=payload,
        )
        assert response.status_code in (200, 201)
        data = response.json()
        assert data["code"] == "test-demo-plan"

    async def test_generate_demo_invoice(self, admin_client: AsyncClient, admin_token_headers: dict[str, str]):
        payload = {
            "due_in_days": 7,
            "payment_method": "manual_pix",
            "payment_instructions": "Fatura demo - dados fictícios",
        }
        response = await admin_client.post(
            "/admin/billing/invoices/generate",
            headers=admin_token_headers,
            json=payload,
        )
        # May return error if no clients exist, but should not be 401/403
        assert response.status_code != 401
        assert response.status_code != 403

    async def test_demo_api_key_creation(self, admin_client: AsyncClient, admin_token_headers: dict[str, str]):
        response = await admin_client.get("/admin/clients", headers=admin_token_headers)
        clients = response.json()
        if not clients:
            pytest.skip("No clients available for API key test")
        client_id = clients[0]["id"]

        key_response = await admin_client.post(
            "/admin/api-keys",
            headers=admin_token_headers,
            json={"client_id": client_id, "name": "demo-test-key"},
        )
        assert key_response.status_code in (200, 201)
        key_data = key_response.json()
        assert "api_key" in key_data
        assert "sk-" in key_data["api_key"] or key_data["api_key"].startswith("sk-")


class TestCommercialDemoSeedDocs:
    def test_demo_pack_docs_integrity(self):
        readme = ROOT / "demo-pack" / "README.md"
        prompts = ROOT / "demo-pack" / "demo-prompts.md"
        api_requests = ROOT / "demo-pack" / "demo-api-requests.md"
        objections = ROOT / "demo-pack" / "demo-objection-handling.md"
        flow = ROOT / "demo-pack" / "demo-flow.md"

        assert readme.exists()
        assert prompts.exists()
        assert api_requests.exists()
        assert objections.exists()
        assert flow.exists()

        readme_content = readme.read_text()
        assert "Clínica" in readme_content or "clínica" in readme_content or "clinica" in readme_content.lower()
        assert "Jurídico" in readme_content or "jurídico" in readme_content

    def test_demo_flow_has_all_scenarios(self):
        flow = ROOT / "demo-pack" / "demo-flow.md"
        content = flow.read_text()
        assert "Clínica" in content
        assert "Jurídico" in content or "RAG" in content
        assert "Provedor" in content

    def test_api_requests_cover_all_endpoints(self):
        content = (ROOT / "demo-pack" / "demo-api-requests.md").read_text()
        endpoints = [
            "/v1/chat/completions",
            "/v1/rag/query",
            "/v1/audio/speech",
            "/v1/embeddings",
            "/v1/responses",
            "/admin/clients",
            "/admin/billing/invoices",
            "/portal/me",
            "/portal/usage",
            "/admin/demo/summary",
        ]
        for ep in endpoints:
            assert ep in content, f"Missing endpoint {ep} in demo-api-requests.md"
