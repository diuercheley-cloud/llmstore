import os
import pytest

DOCS_DIR = "docs/integrations"
REQUIRED_DOCS = [
    "OPEN_WEBUI.md",
    "N8N.md",
    "LANGCHAIN.md",
    "ANYTHINGLLM.md"
]

@pytest.mark.parametrize("doc_name", REQUIRED_DOCS)
def test_doc_exists(doc_name):
    path = os.path.join(DOCS_DIR, doc_name)
    assert os.path.exists(path), f"Documento {doc_name} não encontrado em {DOCS_DIR}"

@pytest.mark.parametrize("doc_name", REQUIRED_DOCS)
def test_doc_content_requirements(doc_name):
    path = os.path.join(DOCS_DIR, doc_name)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
        
        # Deve mencionar localhost:18080
        assert "localhost:18080" in content, f"{doc_name} deve mencionar localhost:18080"
        
        # Deve ter seção de Limitações
        assert "Limitações" in content, f"{doc_name} deve conter seção 'Limitações'"
        
        # Não deve ter API keys reais (formato sk-...)
        import re
        assert not re.search(r"sk-[a-zA-Z0-9]{32,}", content), f"{doc_name} contém o que parece ser uma API key real"
