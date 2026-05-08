import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

LANDING_PAGE_CANDIDATES = (
    ROOT / "control_plane/app/static/www/index.html",
    ROOT / "app/static/www/index.html",
)


def landing_page_path():
    return next((path for path in LANDING_PAGE_CANDIDATES if path.exists()), LANDING_PAGE_CANDIDATES[0])

def test_landing_page_exists():
    assert landing_page_path().exists()

def test_landing_page_content():
    content = landing_page_path().read_text()
    
    # Main sections
    assert "LLM Local para Empresas" in content
    assert "API compatível com OpenAI" in content
    assert "RAG com documentos internos" in content
    assert "Controle de clientes, planos e uso" in content
    assert "Admin Lab para modelos locais" in content
    assert "Operação em localhost ou servidor próprio" in content
    
    # Demo section
    assert "Demonstração Local" in content
    assert "Client Portal Demo" in content
    assert "Admin Dashboard" in content
    assert "Developer Docs & Exemplos" in content
    assert "Exemplos →" in content
    
    # Use cases
    assert "Chatbot com Documentos" in content
    assert "Escritórios e Consultoria" in content
    assert "Imobiliárias e Contabilidade" in content
    
    # Out of scope
    assert "Fora do escopo nesta versão" in content
    assert "Sem PIX/PSP real nesta versão" in content
    assert "PIX real ativo" not in content
    assert "PSP real ativo" not in content

def test_landing_page_local_links():
    content = landing_page_path().read_text()
    
    assert 'href="/portal/"' in content
    assert 'href="/admin/"' in content
    assert 'href="/docs"' in content
    assert 'href="/examples"' in content
    assert 'href="/getting-started"' in content
