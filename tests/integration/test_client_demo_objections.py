from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OBJECTIONS_DOC = ROOT / "docs/CLIENT_DEMO_OBJECTIONS.md"
FAQ_DOC = ROOT / "docs/CLIENT_DEMO_FAQ.md"


class TestClientDemoObjectionsStructure:
    def test_objections_doc_exists(self):
        assert OBJECTIONS_DOC.exists(), "docs/CLIENT_DEMO_OBJECTIONS.md não encontrado"

    def test_objections_doc_has_content(self):
        content = OBJECTIONS_DOC.read_text()
        assert len(content) > 1000, "Documento muito curto"

    def test_has_multiple_objections(self):
        content = OBJECTIONS_DOC.read_text()
        # Count objection headers
        count = content.count("## Objeção")
        assert count >= 5, f"Poucas objeções: {count}. Mínimo esperado: 5"

    def test_each_objection_has_answer(self):
        content = OBJECTIONS_DOC.read_text()
        sections = content.split("## Objeção")
        for section in sections[1:]:  # Skip header
            assert (
                "**Resposta:**" in section or "**Resposta**" in section or "Resposta:" in section
            ), f"Objeção sem resposta encontrada: {section[:100]}"


class TestClientDemoObjectionsContent:
    def test_objection_openai_direct(self):
        content = OBJECTIONS_DOC.read_text()
        assert "OpenAI direto" in content or "OpenAI" in content, (
            "Objeção 'Por que não usar OpenAI direto?' não encontrada"
        )

    def test_objection_model_quality(self):
        content = OBJECTIONS_DOC.read_text()
        assert "modelo local for pior" in content or "pior que" in content, (
            "Objeção 'modelo local pior' não encontrada"
        )

    def test_objection_security(self):
        content = OBJECTIONS_DOC.read_text()
        assert "Isso é seguro" in content or "segurança" in content.lower(), (
            "Objeção de segurança não encontrada"
        )

    def test_objection_support(self):
        content = OBJECTIONS_DOC.read_text()
        assert "suporte" in content.lower(), "Objeção de suporte não encontrada"

    def test_objection_cost(self):
        content = OBJECTIONS_DOC.read_text()
        assert "Quanto custa" in content or "custo" in content.lower(), (
            "Objeção de custo não encontrada"
        )

    def test_objection_integration(self):
        content = OBJECTIONS_DOC.read_text()
        assert "integrar com sistemas internos" in content or "integração" in content.lower(), (
            "Objeção de integração não encontrada"
        )

    def test_objection_lgpd(self):
        content = OBJECTIONS_DOC.read_text()
        assert "LGPD" in content, "Objeção LGPD não encontrada"

    def test_objection_gpu_failure(self):
        content = OBJECTIONS_DOC.read_text()
        assert "GPU falhar" in content or "GPU" in content or "falha" in content.lower(), (
            "Objeção de falha de GPU não encontrada"
        )

    def test_objection_scalability(self):
        content = OBJECTIONS_DOC.read_text()
        assert (
            "Como escalar" in content or "escalar" in content.lower() or "escala" in content.lower()
        ), "Objeção de escalabilidade não encontrada"


class TestClientDemoObjectionsDisclaimers:
    def test_disclaims_psp_pix(self):
        content = OBJECTIONS_DOC.read_text().lower()
        mentions_psp = "psp" in content
        mentions_pix = "pix" in content
        if mentions_psp or mentions_pix:
            assert any(
                phrase in content
                for phrase in [
                    "sem psp",
                    "psp real",
                    "fora do escopo",
                    "billing manual",
                    "faturamento manual",
                ]
            ), "Objeções mencionam PSP/PIX sem disclaimer"

    def test_disclaims_cloud_managed(self):
        content = OBJECTIONS_DOC.read_text()
        # Should mention it's NOT cloud managed
        assert "cloud gerenciada" in content.lower() or any(
            phrase in content.lower()
            for phrase in [
                "não oferecemos cloud",
                "on-premise",
                "appliance local",
                "100% local",
            ]
        ), "Objeções não deixam claro que não é cloud gerenciada"

    def test_disclaims_security_absolute(self):
        content = OBJECTIONS_DOC.read_text().lower()
        # Should not promise absolute security
        if "garantimos segurança absoluta" in content:
            # Must negate it
            context_before = content.split("garantimos segurança absoluta")[0]
            last_sentence = context_before.split(".")[-1]
            assert "não" in last_sentence, "Documento parece prometer segurança absoluta sem negar"

    def test_disclaims_legal_substitution(self):
        content = OBJECTIONS_DOC.read_text().lower()
        assert any(
            phrase in content
            for phrase in [
                "não substitui análise jurídica",
                "não substitui análise de compliance",
                "consulte seu departamento jurídico",
                "não substituímos",
            ]
        ), "Objeções não deixam claro que não substituem análise jurídica"


class TestClientDemoFAQ:
    def test_faq_doc_exists(self):
        assert FAQ_DOC.exists(), "docs/CLIENT_DEMO_FAQ.md não encontrado"

    def test_faq_has_required_questions(self):
        content = FAQ_DOC.read_text().lower()
        required = [
            "sem internet",
            "gpu",
            "modelos suporta",
            "controla custo",
            "vazamento de dados",
            "backup",
            "atualiza",
            "cria clientes",
            "billing",
            "openai sdk",
            "langchain",
        ]
        for topic in required:
            assert topic in content, f"FAQ não cobre o tópico: {topic}"

    def test_faq_disclaims_psp_pix(self):
        content = FAQ_DOC.read_text().lower()
        assert "psp" in content or "pix" in content
        assert "sem psp" in content or "psp real" in content or "manual" in content

    def test_faq_disclaims_fictional_data(self):
        content = FAQ_DOC.read_text().lower()
        assert "fictícios" in content or "dados demo" in content

    def test_faq_mentions_local_appliance(self):
        content = FAQ_DOC.read_text().lower()
        assert "appliance local" in content or "local" in content or "on-premise" in content

    def test_faq_mentions_urls(self):
        content = FAQ_DOC.read_text()
        assert "localhost:18080" in content
        assert "/admin-dashboard" in content
        assert "/client-portal" in content
