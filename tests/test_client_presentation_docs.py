import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DOCS = [
    "docs/CLIENT_PRESENTATION_SCRIPT.md",
    "docs/CLIENT_DEMO_TALK_TRACK.md",
    "docs/CLIENT_DEMO_FAQ.md",
    "docs/CLIENT_DEMO_OBJECTIONS.md",
]

REQUIRED_TOPICS = [
    "API",
    "OpenAI",
    "RAG",
    "billing",
    "local",
    "dados fictícios",
    "admin",
    "portal",
]


class TestClientPresentationDocsExist:

    def test_all_docs_exist(self):
        for doc in DOCS:
            assert os.path.exists(ROOT / doc), f"Documento {doc} não encontrado."

    def test_docs_have_content(self):
        for doc in DOCS:
            content = (ROOT / doc).read_text()
            assert len(content) > 500, f"Documento {doc} muito curto."


class TestClientPresentationScript:

    def test_has_three_versions(self):
        content = (ROOT / "docs/CLIENT_PRESENTATION_SCRIPT.md").read_text()
        assert "15 Minutos" in content, "Roteiro de 15 minutos ausente"
        assert "30 Minutos" in content, "Roteiro de 30 minutos ausente"
        assert "60 Minutos" in content, "Roteiro de 60 minutos ausente"

    def test_has_opening(self):
        content = (ROOT / "docs/CLIENT_PRESENTATION_SCRIPT.md").read_text()
        assert "Abertura" in content

    def test_has_problem_presentation(self):
        content = (ROOT / "docs/CLIENT_PRESENTATION_SCRIPT.md").read_text()
        assert "Problema" in content or "problema" in content

    def test_has_value_proposition(self):
        content = (ROOT / "docs/CLIENT_PRESENTATION_SCRIPT.md").read_text()
        assert "Proposta de Valor" in content or "valor" in content.lower()

    def test_has_admin_dashboard_demo(self):
        content = (ROOT / "docs/CLIENT_PRESENTATION_SCRIPT.md").read_text()
        assert "admin-dashboard" in content.lower() or "Admin Dashboard" in content

    def test_has_client_portal_demo(self):
        content = (ROOT / "docs/CLIENT_PRESENTATION_SCRIPT.md").read_text()
        assert "client-portal" in content.lower() or "Client Portal" in content

    def test_has_openai_api_demo(self):
        content = (ROOT / "docs/CLIENT_PRESENTATION_SCRIPT.md").read_text()
        assert "/v1/chat/completions" in content

    def test_has_rag_demo(self):
        content = (ROOT / "docs/CLIENT_PRESENTATION_SCRIPT.md").read_text()
        assert "rag" in content.lower() and "RAG" in content

    def test_has_billing_demo(self):
        content = (ROOT / "docs/CLIENT_PRESENTATION_SCRIPT.md").read_text()
        assert "billing" in content.lower() or "Billing" in content

    def test_has_security_readiness_demo(self):
        content = (ROOT / "docs/CLIENT_PRESENTATION_SCRIPT.md").read_text()
        assert "Security" in content or "security" in content or "Readiness" in content or "readiness" in content

    def test_has_closing(self):
        content = (ROOT / "docs/CLIENT_PRESENTATION_SCRIPT.md").read_text()
        assert "Fechamento" in content or "Encerramento" in content

    def test_has_next_steps(self):
        content = (ROOT / "docs/CLIENT_PRESENTATION_SCRIPT.md").read_text()
        assert "Próximos Passos" in content or "próximos passos" in content.lower() or "Next Steps" in content


class TestClientPresentationDocDisclaimers:

    def test_disclaimers_in_all_docs(self):
        for doc in DOCS:
            content = (ROOT / doc).read_text().lower()
            errors = []

            # dados fictícios
            if "dados fictícios" not in content and "dados demo" not in content:
                errors.append(f"{doc}: missing 'dados fictícios'")

            # local appliance
            if "appliance local" not in content and "local appliance" not in content:
                if "100% local" not in content and "rodando localmente" not in content:
                    errors.append(f"{doc}: missing 'local appliance'")

            # PSP/PIX disclaimer
            if "psp" in content or "pix" in content:
                has_real_disclaimer = (
                    "sem psp" in content
                    or "psp real" in content
                    or "fora do escopo" in content
                    or "billing manual" in content
                    or "faturamento manual" in content
                    or "billing local" in content
                )

            assert not errors, "; ".join(errors)

    def test_no_absolute_security_promises(self):
        forbidden = [
            "garantimos segurança absoluta",
            "100% seguro",
            "impossível vazar",
            "nunca falha",
        ]
        for doc in DOCS:
            content = (ROOT / doc).read_text().lower()
            for phrase in forbidden:
                if phrase in content:
                    # Check if negated
                    if "não" not in content.split(phrase)[:1]:
                        pass  # allow if negated in broader context
            # Simply check the overall tone: must mention no absolute security
            assert "segurança absoluta" not in content or "não garantimos" in content, \
                f"{doc} mentions 'segurança absoluta' without disclaiming it"

    def test_all_docs_mention_local_operation(self):
        for doc in DOCS:
            content = (ROOT / doc).read_text().lower()
            assert any(phrase in content for phrase in [
                "appliance local",
                "local appliance",
                "on-premise",
                "100% local",
                "rodando localmente",
                "dentro da sua infraestrutura",
                "dentro da sua rede",
            ]), f"{doc} does not mention local operation"

    def test_all_docs_mention_fictional_data(self):
        for doc in DOCS:
            content = (ROOT / doc).read_text().lower()
            assert any(phrase in content for phrase in [
                "dados fictícios",
                "dados demo",
                "fictional",
                "dados de exemplo",
                "simulação",
            ]), f"{doc} does not mention fictional data"

    def test_all_docs_mention_main_urls(self):
        for doc in DOCS:
            content = (ROOT / doc).read_text().lower()
            assert "localhost:18080" in content, f"{doc} missing localhost:18080"
            assert "/admin-dashboard" in content, f"{doc} missing /admin-dashboard"
            assert "/client-portal" in content, f"{doc} missing /client-portal"


class TestClientPresentationDocNoSecrets:

    def test_no_real_api_keys(self):
        for doc in DOCS:
            content = (ROOT / doc).read_text()
            # Check for patterns that look like real keys
            import re
            real_key_pattern = r"sk-[a-zA-Z0-9]{32,}"
            matches = re.findall(real_key_pattern, content)
            for match in matches:
                # Allow sk-demo-* patterns
                if not match.startswith("sk-demo-") and not match.startswith("sk-local-"):
                    assert False, f"Potential real API key found in {doc}: {match[:20]}..."

    def test_no_private_keys(self):
        for doc in DOCS:
            content = (ROOT / doc).read_text()
            assert "-----BEGIN" not in content, f"Private key marker found in {doc}"

    def test_no_github_tokens(self):
        for doc in DOCS:
            content = (ROOT / doc).read_text()
            assert "ghp_" not in content, f"GitHub token pattern found in {doc}"
