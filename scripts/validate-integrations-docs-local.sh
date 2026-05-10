#!/bin/bash
# scripts/validate-integrations-docs-local.sh
# Valida documentação e exemplos de integração

set -e

echo "=== Validando Documentação de Integração ==="

DOCS=(
    "docs/integrations/OPEN_WEBUI.md"
    "docs/integrations/N8N.md"
    "docs/integrations/LANGCHAIN.md"
    "docs/integrations/ANYTHINGLLM.md"
)

EXIT_CODE=0

for doc in "${DOCS[@]}"; do
    if [ ! -f "$doc" ]; then
        echo "[ERROR] Documento não encontrado: $doc"
        EXIT_CODE=1
        continue
    fi

    # Validar menção a localhost:18080
    if ! grep -q "localhost:18080" "$doc"; then
        echo "[ERROR] Documento $doc não menciona localhost:18080"
        EXIT_CODE=1
    fi

    # Validar menção a Limitações
    if ! grep -q "Limitações" "$doc"; then
        echo "[ERROR] Documento $doc não contém seção de Limitações"
        EXIT_CODE=1
    fi

    # Validar ausência de API keys reais (ex: sk- seguido de muitos caracteres)
    if grep -qE "sk-[a-zA-Z0-9]{32,}" "$doc"; then
        echo "[ERROR] Documento $doc parece conter uma API Key real"
        EXIT_CODE=1
    fi

    echo "[OK] $doc"
done

echo "=== Validando Exemplos ==="

EXAMPLES=(
    "examples/langchain/chat.py"
    "examples/langchain/embeddings.py"
    "examples/n8n/README.md"
    "examples/openwebui/README.md"
    "examples/anythingllm/README.md"
)

for example in "${EXAMPLES[@]}"; do
    if [ ! -f "$example" ]; then
        echo "[ERROR] Exemplo não encontrado: $example"
        EXIT_CODE=1
        continue
    fi

    # Validar ausência de secrets
    if grep -qE "sk-[a-zA-Z0-9]{32,}" "$example"; then
        echo "[ERROR] Exemplo $example parece conter segredos"
        EXIT_CODE=1
    fi
    echo "[OK] $example"
done

# Validação do LangChain se instalado
if python3 -c "import langchain_openai" &> /dev/null; then
    echo "=== Testando Sintaxe do Exemplo LangChain ==="
    python3 -m py_compile examples/langchain/chat.py
    python3 -m py_compile examples/langchain/embeddings.py
    echo "[OK] Sintaxe LangChain validada"
else
    echo "[SKIP] langchain-openai não instalado, pulando teste de sintaxe"
fi

if [ $EXIT_CODE -eq 0 ]; then
    echo "=== Todas as validações passaram! ==="
else
    echo "=== Falha na validação! ==="
fi

exit $EXIT_CODE
