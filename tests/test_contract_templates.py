import os
import pytest

CONTRACTS_DIR = "contracts"
REQUIRED_TEMPLATES = [
    "SOW_TEMPLATE.md",
    "SERVICE_AGREEMENT_TEMPLATE.md",
    "SUPPORT_TERMS_TEMPLATE.md",
    "ACCEPTANCE_CRITERIA_TEMPLATE.md",
    "README.md",
]


def test_all_templates_exist():
    for tpl in REQUIRED_TEMPLATES:
        path = os.path.join(CONTRACTS_DIR, tpl)
        assert os.path.isfile(path), f"Missing template: {tpl}"


def test_legal_disclaimer_present():
    for tpl in REQUIRED_TEMPLATES:
        path = os.path.join(CONTRACTS_DIR, tpl)
        with open(path, "r") as f:
            content = f.read().lower()
        assert ("revisão jurídica" in content or
                "revisão por assessoria jurídica" in content or
                "não constitui aconselhamento jurídico" in content or
                "template genérico" in content), (
            f"{tpl} is missing legal disclaimer"
        )


def test_local_appliance_mentioned():
    for tpl in REQUIRED_TEMPLATES:
        if tpl == "README.md":
            continue
        path = os.path.join(CONTRACTS_DIR, tpl)
        with open(path, "r") as f:
            content = f.read().lower()
        assert "local appliance" in content, (
            f"{tpl} does not mention local appliance"
        )


def test_psp_pix_out_of_scope():
    for tpl in ["SOW_TEMPLATE.md", "SERVICE_AGREEMENT_TEMPLATE.md"]:
        path = os.path.join(CONTRACTS_DIR, tpl)
        with open(path, "r") as f:
            content = f.read().lower()
        assert ("psp" in content or "pix" in content or
                "pagamentos reais" in content or
                "processamento de pagamentos" in content), (
            f"{tpl} missing PSP/PIX limitation"
        )


def test_no_absolute_performance_guarantees():
    for tpl in REQUIRED_TEMPLATES:
        if tpl == "README.md":
            continue
        path = os.path.join(CONTRACTS_DIR, tpl)
        with open(path, "r") as f:
            content = f.read().lower()
        forbidden = [
            "garantimos 100%",
            "100% de disponibilidade",
            "uptime garantido",
            "sla garantido de 100%",
            "performance garantida",
        ]
        for phrase in forbidden:
            assert phrase not in content, (
                f"{tpl} contains absolute guarantee: {phrase}"
            )


def test_no_automatic_compliance_claims():
    for tpl in REQUIRED_TEMPLATES:
        if tpl == "README.md":
            continue
        path = os.path.join(CONTRACTS_DIR, tpl)
        with open(path, "r") as f:
            content = f.read().lower()
        # Allow negation phrases like "não garante compliance automático"
        # but flag positive claims
        lines = content.split("\n")
        for line in lines:
            if "compliance automático" in line and not any(
                neg in line for neg in ["não ", "sem ", "exceto"]
            ):
                pytest.fail(f"{tpl} claims automatic compliance: {line.strip()}")


def test_no_real_data():
    for tpl in REQUIRED_TEMPLATES:
        path = os.path.join(CONTRACTS_DIR, tpl)
        with open(path, "r") as f:
            content = f.read()
        # Real CNPJ/CPF patterns (00.000.000/0001-00 is a placeholder)
        # We check that the only CNPJ-like pattern is the placeholder
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if "00.000.000/0001-00" in line or "XX.XXX.XXX" in line:
                continue
            assert "cnpj" not in line.lower() or "XX." in line, (
                f"{tpl}:{i+1} may contain real CNPJ data"
            )


def test_sow_contains_required_sections():
    path = os.path.join(CONTRACTS_DIR, "SOW_TEMPLATE.md")
    with open(path, "r") as f:
        content = f.read().lower()
    required_sections = [
        "partes",
        "escopo",
        "fora do escopo",
        "entregáveis",
        "ambiente local",
        "requisitos do cliente",
        "cronograma",
        "critérios de aceite",
        "suporte",
        "limitações técnicas",
        "segurança",
        "backups",
        "confidencialidade",
        "lgpd",
        "revisão jurídica obrigatória",
    ]
    for section in required_sections:
        assert section in content, (
            f"SOW_TEMPLATE.md missing required section: {section}"
        )


def test_service_agreement_contains_required_sections():
    path = os.path.join(CONTRACTS_DIR, "SERVICE_AGREEMENT_TEMPLATE.md")
    with open(path, "r") as f:
        content = f.read().lower()
    required_sections = [
        "prestação de serviço",
        "responsabilidade das partes",
        "disponibilidade local",
        "manutenção",
        "atualização",
        "propriedade dos dados",
        "exclusões",
        "pagamento",
        "rescisão",
    ]
    for section in required_sections:
        assert section in content, (
            f"SERVICE_AGREEMENT_TEMPLATE.md missing required section: {section}"
        )
