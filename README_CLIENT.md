# Client API SDK

Este SDK facilita a integração com a LLM Inference Stack.

## Instalação

Certifique-se de ter o `httpx` instalado:

```bash
pip install httpx
```

## Uso Rápido

```python
from llm_stack_client import LLMStackClient

client = LLMStackClient(
    api_key="sua_chave_aqui",
    base_url="http://api.seudominio.com"
)

# Chat
response = client.chat_completions(
    messages=[{"role": "user", "content": "Olá!"}]
)
print(response["choices"][0]["message"]["content"])

# Consultar Uso
usage = client.get_usage()
print(f"Tokens usados hoje: {usage['daily_usage']['used_tokens']}")
```

## Funcionalidades

- **Inferência**: Chat Completions (compatível com OpenAI), Listagem de Modelos.
- **Gestão**: Informações da conta, Listagem e Criação de API Keys, Histórico de faturamento.
- **RAG (Busca Semântica)**: Upload de documentos (.pdf, .txt, .md) e busca semântica integrada.

## Exemplos

Veja a pasta `examples/` para um guia completo de uso.
