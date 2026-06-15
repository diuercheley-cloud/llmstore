import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

TEMPLATES = [
    "proposals/TECHNICAL_PROPOSAL_TEMPLATE.md",
    "proposals/COMMERCIAL_PROPOSAL_TEMPLATE.md",
    "proposals/LOCAL_AI_APPLIANCE_ONE_PAGER.md",
    "proposals/README.md",
]


class TestProposalTemplatesExist:
    def test_all_templates_exist(self):
        for t in TEMPLATES:
            assert os.path.exists(ROOT / t), f"Template {t} não encontrado"

    def test_templates_have_content(self):
        for t in TEMPLATES:
            content = (ROOT / t).read_text()
            assert len(content) > 500, f"Template {t} muito curto"


class TestTechnicalProposalTemplate:
    def test_has_overview(self):
        content = (ROOT / "proposals/TECHNICAL_PROPOSAL_TEMPLATE.md").read_text()
        assert "Visão Geral" in content or "visão geral" in content.lower()

    def test_has_architecture(self):
        content = (ROOT / "proposals/TECHNICAL_PROPOSAL_TEMPLATE.md").read_text()
        assert "Arquitetura" in content or "arquitetura" in content.lower()

    def test_has_components(self):
        content = (ROOT / "proposals/TECHNICAL_PROPOSAL_TEMPLATE.md").read_text()
        assert "Componentes" in content or "componentes" in content.lower()

    def test_has_hardware_requirements(self):
        content = (ROOT / "proposals/TECHNICAL_PROPOSAL_TEMPLATE.md").read_text()
        assert "Requisitos de Hardware" in content or "hardware" in content.lower()

    def test_has_software_requirements(self):
        content = (ROOT / "proposals/TECHNICAL_PROPOSAL_TEMPLATE.md").read_text()
        assert "Requisitos de Software" in content or "software" in content.lower()

    def test_has_security(self):
        content = (ROOT / "proposals/TECHNICAL_PROPOSAL_TEMPLATE.md").read_text()
        assert "Segurança" in content or "segurança" in content.lower()

    def test_has_local_operation(self):
        content = (ROOT / "proposals/TECHNICAL_PROPOSAL_TEMPLATE.md").read_text()
        assert "Operação Local" in content or "operação local" in content.lower()

    def test_has_backups(self):
        content = (ROOT / "proposals/TECHNICAL_PROPOSAL_TEMPLATE.md").read_text()
        assert "Backup" in content or "backup" in content.lower()

    def test_has_upgrade_rollback(self):
        content = (ROOT / "proposals/TECHNICAL_PROPOSAL_TEMPLATE.md").read_text()
        assert (
            "Upgrade" in content
            or "upgrade" in content.lower()
            or "Rollback" in content
            or "rollback" in content.lower()
        )

    def test_has_rag(self):
        content = (ROOT / "proposals/TECHNICAL_PROPOSAL_TEMPLATE.md").read_text()
        assert "RAG" in content

    def test_has_tts(self):
        content = (ROOT / "proposals/TECHNICAL_PROPOSAL_TEMPLATE.md").read_text()
        assert "TTS" in content

    def test_has_openai_compatibility(self):
        content = (ROOT / "proposals/TECHNICAL_PROPOSAL_TEMPLATE.md").read_text()
        assert "OpenAI" in content

    def test_has_limitations(self):
        content = (ROOT / "proposals/TECHNICAL_PROPOSAL_TEMPLATE.md").read_text()
        assert "Limitações" in content or "limitações" in content.lower()

    def test_has_excluded_scope(self):
        content = (ROOT / "proposals/TECHNICAL_PROPOSAL_TEMPLATE.md").read_text()
        assert "Escopo Excluído" in content or "escopo excluído" in content.lower()

    def test_has_implementation_plan(self):
        content = (ROOT / "proposals/TECHNICAL_PROPOSAL_TEMPLATE.md").read_text()
        assert "Plano de Implantação" in content or "implantação" in content.lower()

    def test_has_acceptance_criteria(self):
        content = (ROOT / "proposals/TECHNICAL_PROPOSAL_TEMPLATE.md").read_text()
        assert "Critérios de Aceite" in content or "aceite" in content.lower()


class TestCommercialProposalTemplate:
    def test_has_problem(self):
        content = (ROOT / "proposals/COMMERCIAL_PROPOSAL_TEMPLATE.md").read_text()
        assert "Problema" in content or "problema" in content.lower()

    def test_has_solution(self):
        content = (ROOT / "proposals/COMMERCIAL_PROPOSAL_TEMPLATE.md").read_text()
        assert "Solução" in content or "solução" in content.lower()

    def test_has_benefits(self):
        content = (ROOT / "proposals/COMMERCIAL_PROPOSAL_TEMPLATE.md").read_text()
        assert "Benefícios" in content or "benefícios" in content.lower()

    def test_has_plans(self):
        content = (ROOT / "proposals/COMMERCIAL_PROPOSAL_TEMPLATE.md").read_text()
        assert "Planos" in content or "planos" in content.lower()

    def test_has_costs_as_placeholders(self):
        content = (ROOT / "proposals/COMMERCIAL_PROPOSAL_TEMPLATE.md").read_text()
        assert "R$ [" in content or "[ Valor ]" in content or "Sob consulta" in content

    def test_has_timeline(self):
        content = (ROOT / "proposals/COMMERCIAL_PROPOSAL_TEMPLATE.md").read_text()
        assert "Cronograma" in content or "cronograma" in content.lower()

    def test_has_supplier_responsibilities(self):
        content = (ROOT / "proposals/COMMERCIAL_PROPOSAL_TEMPLATE.md").read_text()
        assert "Responsabilidades do Fornecedor" in content

    def test_has_client_responsibilities(self):
        content = (ROOT / "proposals/COMMERCIAL_PROPOSAL_TEMPLATE.md").read_text()
        assert "Responsabilidades do Cliente" in content

    def test_has_support_section(self):
        content = (ROOT / "proposals/COMMERCIAL_PROPOSAL_TEMPLATE.md").read_text()
        assert "Suporte" in content or "suporte" in content.lower()

    def test_has_next_steps(self):
        content = (ROOT / "proposals/COMMERCIAL_PROPOSAL_TEMPLATE.md").read_text()
        assert "Próximos Passos" in content or "próximos passos" in content.lower()


class TestOnePager:
    def test_has_title(self):
        content = (ROOT / "proposals/LOCAL_AI_APPLIANCE_ONE_PAGER.md").read_text()
        assert "# " in content

    def test_has_value_proposition(self):
        content = (ROOT / "proposals/LOCAL_AI_APPLIANCE_ONE_PAGER.md").read_text()
        assert "Proposta de Valor" in content or "valor" in content.lower()

    def test_has_key_features(self):
        content = (ROOT / "proposals/LOCAL_AI_APPLIANCE_ONE_PAGER.md").read_text()
        assert "Recursos" in content or "recursos" in content.lower() or "Features" in content

    def test_has_target_audience(self):
        content = (ROOT / "proposals/LOCAL_AI_APPLIANCE_ONE_PAGER.md").read_text()
        assert "Para Quem Serve" in content or "para quem" in content.lower()

    def test_has_requirements(self):
        content = (ROOT / "proposals/LOCAL_AI_APPLIANCE_ONE_PAGER.md").read_text()
        assert "Requisitos" in content or "requisitos" in content.lower()

    def test_has_limitations(self):
        content = (ROOT / "proposals/LOCAL_AI_APPLIANCE_ONE_PAGER.md").read_text()
        assert "Limitações" in content or "limitações" in content.lower()


class TestProposalDisclaimers:
    def test_local_appliance_mentioned(self):
        for t in TEMPLATES:
            content = (ROOT / t).read_text().lower()
            assert any(
                phrase in content
                for phrase in [
                    "appliance local",
                    "local appliance",
                    "on-premise",
                    "appliance local",
                    "local ai appliance",
                ]
            ), f"{t} não menciona local appliance"

    def test_psp_pix_out_of_scope(self):
        for t in TEMPLATES:
            content = (ROOT / t).read_text().lower()
            if "psp" in content or "pix" in content:
                assert any(
                    phrase in content
                    for phrase in [
                        "sem psp",
                        "psp real",
                        "pix real",
                        "fora do escopo",
                        "billing.*manual",
                        "faturamento.*manual",
                        "sem psp/pix",
                    ]
                ) or ("manual" in content and ("pix" in content or "psp" in content)), (
                    f"{t} menciona PSP/PIX mas não deixa claro que está fora do escopo"
                )

    def test_no_absolute_security_promises(self):
        for t in TEMPLATES:
            content = (ROOT / t).read_text().lower()
            # Should mention security but not promise absolute
            if "garantimos segurança absoluta" in content:
                idx = content.index("garantimos segurança absoluta")
                prev = content[max(0, idx - 200) : idx]
                assert "não" in prev, f"{t} parece prometer segurança absoluta"
