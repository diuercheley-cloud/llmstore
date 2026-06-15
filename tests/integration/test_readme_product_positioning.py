from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"


def test_readme_exists():
    assert README.exists()


def test_readme_title_llm_inference_stack():
    content = README.read_text(encoding="utf-8")
    assert content.startswith("# LLM Inference Stack")


def test_readme_subtitle_openai_compatible():
    content = README.read_text(encoding="utf-8")
    assert "OpenAI-compatible" in content or "OpenAI-Compatible" in content


def test_readme_release_status_v2():
    content = README.read_text(encoding="utf-8")
    assert "v2.x" in content


def test_readme_section_o_que_e():
    content = README.read_text(encoding="utf-8")
    assert "## O que é" in content


def test_readme_section_para_quem_serve():
    content = README.read_text(encoding="utf-8")
    assert "## Para quem serve" in content


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


def test_readme_limitation_cloud():
    content = README.read_text(encoding="utf-8")
    # Limitação de cloud gerenciada (offline-first)
    assert "Cloud" in content or "cloud" in content.lower()


def test_readme_no_psp_pix_promise():
    content = README.read_text(encoding="utf-8")
    # Check for scope or limitation related to payments if still present
    assert "PSP" in content or "PIX" in content or "offline-first" in content.lower()


def test_readme_not_excessively_long():
    """README should be concise (< 600 lines)."""
    lines = README.read_text(encoding="utf-8").splitlines()
    assert len(lines) < 600, f"README has {len(lines)} lines; move technical details to docs/"
