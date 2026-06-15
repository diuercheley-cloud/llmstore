import os

import pytest

DOC = "docs/PAID_IMPLEMENTATION_CHECKLIST.md"
REQUIRED_SECTIONS = [
    "Antes da Implantação",
    "Requisitos de Hardware",
    "Requisitos de Acesso",
    "Responsabilidades do Cliente",
    "Responsabilidades do Fornecedor",
    "Backup Inicial",
    "Instalação",
    "Configuração",
    "Modelos",
    "Segurança",
    "Testes de Aceite",
    "Treinamento do Operador",
    "Entrega Final",
    "Pós-Implantação",
    "Assinaturas",
]
VALID_STATUSES = [
    "NOT_STARTED",
    "IN_PROGRESS",
    "BLOCKED",
    "READY_FOR_ACCEPTANCE",
    "ACCEPTED",
]


def test_document_exists():
    assert os.path.isfile(DOC), f"Document not found: {DOC}"


def test_all_required_sections_present():
    with open(DOC) as f:
        content = f.read()
    for section in REQUIRED_SECTIONS:
        assert section in content, f"Missing required section: {section}"


def test_mentions_backup():
    with open(DOC) as f:
        content = f.read().lower()
    assert "backup" in content, "Document should mention backup"


def test_mentions_acceptance_criteria():
    with open(DOC) as f:
        content = f.read()
    assert any(
        phrase in content.lower()
        for phrase in ["critério de aceite", "aceite", "acceptance", "Testes de Aceite"]
    ), "Document should mention acceptance criteria"


def test_psp_pix_disclaimer():
    with open(DOC) as f:
        content = f.read().lower()
    assert any(
        phrase in content
        for phrase in ["psp", "pix", "pagamentos reais", "processamento de pagamentos"]
    ), "Document missing PSP/PIX disclaimer"


def test_no_absolute_guarantees():
    with open(DOC) as f:
        content = f.read().lower()
    forbidden = [
        "100% de disponibilidade",
        "uptime garantido",
        "performance garantida",
    ]
    for phrase in forbidden:
        assert phrase not in content, f"Contains absolute guarantee: {phrase}"


def test_no_secrets():
    with open(DOC) as f:
        content = f.read()
    secrets_patterns = [
        "sk-",
        "ghp_",
        "-----BEGIN",
        "ADMIN_TOKEN=",
        "JWT_SECRET=",
    ]
    for pattern in secrets_patterns:
        # Only flag if not part of an explanation or example
        if pattern in content:
            lines = content.split("\n")
            for line in lines:
                if (
                    pattern in line
                    and "exemplo" not in line.lower()
                    and "example" not in line.lower()
                ):
                    pytest.fail(f"Potential secret pattern '{pattern}' found in:\n{line}")


def test_all_statuses_defined():
    with open(DOC) as f:
        content = f.read()
    for status in VALID_STATUSES:
        assert status in content, f"Status definition missing: {status}"


def test_client_provider_responsibilities_separated():
    with open(DOC) as f:
        content = f.read()
    assert "Responsabilidades do Cliente" in content
    assert "Responsabilidades do Fornecedor" in content


def test_no_public_domain_required():
    with open(DOC) as f:
        content = f.read().lower()
    # Should not require public domain or cloud
    assert "domínio público" not in content or "não" in content


def test_no_cloud_requirement():
    with open(DOC) as f:
        content = f.read().lower()
    # Should not require cloud infrastructure
    assert "cloud" not in content
