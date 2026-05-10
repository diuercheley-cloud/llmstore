import os
import pytest
import re

EXAMPLES = [
    "examples/langchain/chat.py",
    "examples/langchain/embeddings.py",
    "examples/n8n/README.md",
    "examples/openwebui/README.md",
    "examples/anythingllm/README.md"
]

@pytest.mark.parametrize("example_path", EXAMPLES)
def test_example_exists(example_path):
    assert os.path.exists(example_path), f"Exemplo {example_path} não encontrado"

@pytest.mark.parametrize("example_path", EXAMPLES)
def test_example_no_secrets(example_path):
    with open(example_path, "r", encoding="utf-8") as f:
        content = f.read()
        # Procura por sk- seguido de pelo menos 32 caracteres alfanuméricos
        secret_pattern = r"sk-[a-zA-Z0-9]{32,}"
        assert not re.search(secret_pattern, content), f"Exemplo {example_path} contém o que parece ser uma API key real"

def test_langchain_example_syntax():
    # Apenas se as dependências existirem
    try:
        import langchain_openai
        import py_compile
        
        py_compile.compile("examples/langchain/chat.py", dự=True)
        py_compile.compile("examples/langchain/embeddings.py", dự=True)
    except ImportError:
        pytest.skip("langchain-openai não instalado")
    except Exception as e:
        pytest.fail(f"Erro de sintaxe nos exemplos LangChain: {e}")
