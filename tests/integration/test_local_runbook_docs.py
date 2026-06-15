import os


def test_runbook_exists():
    assert os.path.exists("docs/LOCAL_PRODUCTION_RUNBOOK.md")


def test_quickstart_exists():
    assert os.path.exists("docs/LOCAL_PRODUCTION_QUICKSTART.md")


def test_readme_references_docs():
    with open("README.md") as f:
        content = f.read()
        assert "docs/LOCAL_PRODUCTION_RUNBOOK.md" in content
        assert "docs/LOCAL_PRODUCTION_QUICKSTART.md" in content
        assert "docs/LOCAL_PRODUCTION_VALIDATION.md" in content


def test_runbook_content():
    with open("docs/LOCAL_PRODUCTION_RUNBOOK.md") as f:
        content = f.read()
        assert "localhost:18080" in content
        assert "validate-local-production-full.sh" in content
        assert "Fora de Escopo" in content
        assert "Gateway de pagamento real (PSP)" in content
        assert "Sem PIX real nesta versão" in content


def test_quickstart_content():
    with open("docs/LOCAL_PRODUCTION_QUICKSTART.md") as f:
        content = f.read()
        assert "local-production-up.sh" in content
        assert "validate-local-production" in content
        assert "localhost:18080" in content
