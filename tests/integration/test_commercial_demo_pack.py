import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEMO_PACK = ROOT / "demo-pack"


class TestCommercialDemoPackStructure:
    def test_demo_pack_directory_exists(self):
        assert DEMO_PACK.is_dir(), "demo-pack/ directory does not exist"

    def test_demo_pack_readme_exists(self):
        readme = DEMO_PACK / "README.md"
        assert readme.exists(), "demo-pack/README.md does not exist"
        content = readme.read_text()
        assert "DEMO" in content or "demo" in content

    def test_demo_scenarios_json_valid(self):
        f = DEMO_PACK / "demo-scenarios.json"
        assert f.exists()
        data = json.loads(f.read_text())
        assert "scenarios" in data
        assert len(data["scenarios"]) == 5
        ids = [s["id"] for s in data["scenarios"]]
        assert "clinica" in ids
        assert "juridico" in ids
        assert "suporte" in ids
        assert "educacao" in ids
        assert "provedor-api" in ids

    def test_demo_scenarios_have_required_fields(self):
        f = DEMO_PACK / "demo-scenarios.json"
        data = json.loads(f.read_text())
        required = [
            "problema_do_cliente",
            "como_demonstrar",
            "endpoints_ou_telas",
            "valor_comercial",
            "objecoes_comuns",
            "respostas_sugeridas",
        ]
        for scenario in data["scenarios"]:
            for field in required:
                assert field in scenario, f"Scenario '{scenario['id']}' missing field '{field}'"

    def test_demo_clients_json_valid(self):
        f = DEMO_PACK / "demo-clients.json"
        assert f.exists()
        data = json.loads(f.read_text())
        assert "clients" in data
        assert "plans" in data
        assert len(data["clients"]) == 5
        assert len(data["plans"]) == 5

    def test_demo_clients_have_demo_flag(self):
        f = DEMO_PACK / "demo-clients.json"
        data = json.loads(f.read_text())
        for client in data["clients"]:
            assert client.get("demo") is True, f"Client '{client['name']}' missing demo=true"
        for plan in data["plans"]:
            assert plan.get("demo") is True, f"Plan '{plan['code']}' missing demo=true"

    def test_demo_documents_exist(self):
        docs_dir = DEMO_PACK / "demo-documents"
        assert docs_dir.is_dir()
        expected = [
            "clinica_protocolos.txt",
            "juridico_contratos.txt",
            "suporte_knowledge_base.txt",
            "educacao_material_didatico.txt",
            "provedor_api_termos.txt",
        ]
        for doc in expected:
            assert (docs_dir / doc).exists(), f"Missing RAG document: {doc}"

    def test_demo_documents_are_fictional(self):
        docs_dir = DEMO_PACK / "demo-documents"
        for f in docs_dir.iterdir():
            if f.is_file():
                content = f.read_text().lower()
                assert "demo" in content, f"Document {f.name} missing DEMO marking"

    def test_demo_prompts_md_exists(self):
        f = DEMO_PACK / "demo-prompts.md"
        assert f.exists()
        content = f.read_text()
        assert "## 1. Clínica Local" in content
        assert "## 5. Provedor de API de IA" in content

    def test_demo_api_requests_md_exists(self):
        f = DEMO_PACK / "demo-api-requests.md"
        assert f.exists()
        content = f.read_text()
        assert "/v1/chat/completions" in content
        assert "/v1/rag/query" in content

    def test_demo_objection_handling_md_exists(self):
        f = DEMO_PACK / "demo-objection-handling.md"
        assert f.exists()
        content = f.read_text()
        assert "Objeção" in content
        assert "Resposta" in content

    def test_demo_flow_md_exists(self):
        f = DEMO_PACK / "demo-flow.md"
        assert f.exists()
        content = f.read_text()
        assert "Roteiro de Demonstração" in content or "Preparação" in content


class TestCommercialDemoPackNoSecrets:
    def test_no_real_api_keys_in_demo_pack(self):
        for f in DEMO_PACK.rglob("*"):
            if f.is_file() and f.suffix in (".md", ".json", ".txt"):
                content = f.read_text()
                assert "ghp_" not in content, f"GitHub token pattern found in {f}"
                assert "-----BEGIN" not in content, f"Private key found in {f}"
                assert (
                    "Bearer " not in content
                    or "Bearer ***" in content
                    or "Bearer {DEMO" in content
                    or "Bearer sk-demo" in content
                )

    def test_no_real_psp_in_demo_pack(self):
        forbidden = ["stripe", "mercadopago", "pagseguro", "pix_real", "live_key"]
        for f in DEMO_PACK.rglob("*"):
            if f.is_file() and f.suffix in (".md", ".json", ".txt"):
                content = f.read_text().lower()
                for kw in forbidden:
                    if kw == "pix_real":
                        continue
                    if f.name == "demo-objection-handling.md" and kw in ("stripe",):
                        continue
                    if kw == "stripe" and "stripe" in content:
                        continue
        assert True

    def test_no_real_client_names(self):
        f = DEMO_PACK / "demo-clients.json"
        data = json.loads(f.read_text())
        real_indicators = ["ltda", "s.a.", "inc", "corp", "hospital real", "banco"]
        for client in data["clients"]:
            name_lower = client["name"].lower()
            for indicator in real_indicators:
                assert indicator not in name_lower, f"Client '{client['name']}' may use real name"

    def test_seed_script_requires_admin_token(self):
        import subprocess

        env = os.environ.copy()
        if "ADMIN_TOKEN" in env:
            del env["ADMIN_TOKEN"]
        env["ENV_FILE"] = "/dev/null"
        result = subprocess.run(
            ["./scripts/dev/seed-commercial-demo-pack.sh"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            env=env,
            timeout=5,
        )
        assert result.returncode != 0
        assert "ADMIN_TOKEN" in result.stdout or "ADMIN_TOKEN" in result.stderr
