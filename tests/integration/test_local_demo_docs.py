import os


def test_demo_docs_exist():
    """Valida se os arquivos de documentação da demo existem."""
    docs = ["docs/LOCAL_DEMO_GUIDE.md", "docs/LOCAL_DEMO_SCRIPT.md", "docs/LOCAL_DEMO_FAQ.md"]
    for doc in docs:
        assert os.path.exists(doc), f"Documento {doc} não encontrado."


def test_readme_links_to_demo_docs():
    """Valida se o README.md aponta para os documentos de demo."""
    with open("README.md") as f:
        content = f.read()

    assert "docs/LOCAL_DEMO_GUIDE.md" in content
    assert "docs/LOCAL_DEMO_SCRIPT.md" in content
    assert "docs/LOCAL_DEMO_FAQ.md" in content


def test_guide_mentions_demo_scripts():
    """Valida se o guia menciona os scripts de seed e reset."""
    with open("docs/LOCAL_DEMO_GUIDE.md") as f:
        content = f.read()

    assert "seed-demo-local.sh" in content
    assert "reset-demo-local.sh" in content


def test_script_has_presentation_sequence():
    """Valida se o roteiro contém uma sequência de apresentação."""
    with open("docs/LOCAL_DEMO_SCRIPT.md") as f:
        content = f.read()

    # Verifica se existem seções numeradas ou tópicos de sequência
    assert "## 1." in content or "Abertura" in content
    assert "## 2." in content or "Visão Geral" in content
    assert "Encerramento" in content


def test_faq_clarifies_psp_out_of_scope():
    """Valida se o FAQ deixa claro que PSP/PIX real está fora de escopo."""
    with open("docs/LOCAL_DEMO_FAQ.md") as f:
        content = f.read()

    # Verifica se menciona que não há integração real/PIX real
    assert "PSP real" in content or "PIX real" in content or "não há integração" in content
    assert "manual" in content.lower()
