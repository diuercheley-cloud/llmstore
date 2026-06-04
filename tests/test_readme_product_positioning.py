from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"


def test_readme_exists():
    assert README.exists()


def test_readme_title_local_ai_appliance():
    content = README.read_text(encoding="utf-8")
    assert content.startswith("# Local AI Appliance")


def test_readme_subtitle_openai_compatible():
    content = README.read_text(encoding="utf-8")
    assert "OpenAI-compatible" in content


def test_readme_release_status():
    content = README.read_text(encoding="utf-8")
    assert "v1.7.0-local-ai-appliance" in content


def test_readme_section_o_que_e():
    content = README.read_text(encoding="utf-8")
    assert "## O que é" in content


def test_readme_section_para_quem_serve():
    content = README.read_text(encoding="utf-8")
    assert "## Para quem serve" in content


def test_readme_section_principais_recursos():
    content = README.read_text(encoding="utf-8")
    assert "## Principais recursos" in content


def test_readme_section_quick_start():
    content = README.read_text(encoding="utf-8")
    assert "## Quick start" in content


def test_readme_section_customer_demo():
    content = README.read_text(encoding="utf-8")
    assert "## Customer demo" in content


def test_readme_section_instalacao_cliente():
    content = README.read_text(encoding="utf-8")
    assert "## Instalação em cliente" in content or "## Instala" in content


def test_readme_section_operacao_diaria():
    content = README.read_text(encoding="utf-8")
    assert "## Operação diária" in content


def test_readme_section_seguranca_readiness():
    content = README.read_text(encoding="utf-8")
    assert "## Segurança / Readiness" in content or "## Seguran" in content


def test_readme_section_limitacoes():
    content = README.read_text(encoding="utf-8")
    assert "## Limitações" in content or "## Limita" in content


def test_readme_section_documentacao():
    content = README.read_text(encoding="utf-8")
    assert "## Documentação" in content or "## Documenta" in content


def test_readme_section_release_history():
    content = README.read_text(encoding="utf-8")
    assert "## Release History" in content


def test_readme_section_roadmap():
    content = README.read_text(encoding="utf-8")
    assert "## Roadmap" in content


def test_readme_references_make_install_local():
    content = README.read_text(encoding="utf-8")
    assert "make install-local" in content


def test_readme_references_make_customer_demo():
    content = README.read_text(encoding="utf-8")
    assert "make customer-demo" in content


def test_readme_references_make_validate():
    content = README.read_text(encoding="utf-8")
    assert "make validate" in content


def test_readme_references_make_security():
    content = README.read_text(encoding="utf-8")
    assert "make security" in content


def test_readme_references_make_readiness():
    content = README.read_text(encoding="utf-8")
    assert "make readiness" in content


def test_readme_references_make_backup():
    content = README.read_text(encoding="utf-8")
    assert "make backup" in content


def test_readme_references_make_rollback():
    content = README.read_text(encoding="utf-8")
    assert "make rollback" in content


def test_readme_limitation_psp():
    content = README.read_text(encoding="utf-8")
    assert "PSP" in content


def test_readme_limitation_pix():
    content = README.read_text(encoding="utf-8")
    assert "PIX" in content


def test_readme_limitation_cloud():
    content = README.read_text(encoding="utf-8")
    assert "Cloud gerenciada" in content or "cloud gerenciada" in content.lower()


def test_readme_limitation_hardware():
    content = README.read_text(encoding="utf-8")
    assert "Modelos dependem do hardware" in content


def test_readme_no_psp_pix_promise():
    content = README.read_text(encoding="utf-8")
    assert "fora do escopo" in content


def test_readme_not_excessively_long():
    """README should be concise (< 400 lines)."""
    lines = README.read_text(encoding="utf-8").splitlines()
    assert len(lines) < 400, (
        f"README has {len(lines)} lines; move technical details to docs/"
    )
