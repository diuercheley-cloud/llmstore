---
owner: platform-ops
status: consolidated
---

# Integração com LangChain

O `llm-inference-stack` integra-se nativamente com LangChain via classe `ChatOpenAI`.

## Status de Compatibilidade
- **Status**: Totalmente Compatível
- **Linguagens**: Python e JavaScript/TypeScript

## Configuração

### Base URL
`http://localhost:18080/v1`

### Exemplo em Python

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    openai_api_base="http://localhost:18080/v1",
    openai_api_key="demo-default",
    model_name="unsloth/gemma-4-E4B-it-GGUF"
)

response = llm.invoke("Olá, como você pode me ajudar?")
print(response.content)
```

## Recursos Suportados
- **Chat Completions**: Sim
- **Streaming**: Sim (`llm.stream(...)`)
- **Embeddings**: Via `OpenAIEmbeddings(openai_api_base="...", ...)`
- **Responses API**: Compatível via chamadas diretas ou wrappers customizados.

## Limitações
- Algumas cadeias complexas que exigem `tools` nativos da OpenAI podem precisar de ajustes dependendo do suporte do modelo local.

## Troubleshooting
- **Erro de Conexão**: Garanta que `openai_api_base` termina em `/v1`.
- **Modelo não encontrado**: Liste os modelos disponíveis para garantir o nome exato.
