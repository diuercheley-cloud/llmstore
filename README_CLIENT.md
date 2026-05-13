# Client API SDK

Este documento descreve como integrar aplicações com o **Local AI Appliance** usando a API OpenAI-compatible.

## Endpoints

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/v1/models` | Lista modelos disponíveis |
| `POST` | `/v1/chat/completions` | Chat completion (stream ou não) |
| `POST` | `/v1/embeddings` | Gera embeddings |
| `POST` | `/v1/responses` | Responses API (beta) |
| `GET` | `/client/usage` | Consulta uso do cliente |

Autenticação: `Authorization: Bearer <API_KEY>`

## Client SDK

Um SDK Python completo está disponível em [`scripts/llm_stack_client.py`](scripts/llm_stack_client.py):

```python
from scripts.llm_stack_client import LLMStackClient

client = LLMStackClient(api_key="sk-local-...", base_url="http://localhost:18080")

# Listar modelos
models = client.list_models()

# Chat completion
response = client.chat_completions(
    messages=[{"role": "user", "content": "Olá!"}],
    model="unsloth/gemma-4-E4B-it-GGUF",
)
```

O SDK cobre chat, listagem de modelos, gerenciamento de portal, RAG e streaming.

## Exemplos

### curl

```bash
# Listar modelos
curl -fsS http://localhost:18080/v1/models \
  -H "Authorization: Bearer ${API_KEY}" | python3 -m json.tool

# Chat completion (stream)
curl -N http://localhost:18080/v1/chat/completions \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "unsloth/gemma-4-E4B-it-GGUF",
    "messages": [{"role": "user", "content": "Explique o que é um appliance de IA local."}],
    "temperature": 0.7,
    "max_tokens": 512,
    "stream": true
  }'

# Chat completion (não-stream)
curl -fsS http://localhost:18080/v1/chat/completions \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "unsloth/gemma-4-E4B-it-GGUF",
    "messages": [{"role": "user", "content": "Responda em uma frase."}],
    "max_tokens": 128,
    "stream": false
  }' | python3 -m json.tool
```

### Python (httpx)

```python
import httpx

api_key = "sk-local-..."  # Substitua pela sua chave
base_url = "http://localhost:18080"

client = httpx.Client(base_url=base_url)

# Listar modelos
resp = client.get("/v1/models", headers={"Authorization": f"Bearer {api_key}"})
print(resp.json())

# Chat completion
resp = client.post(
    "/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    },
    json={
        "model": "unsloth/gemma-4-E4B-it-GGUF",
        "messages": [{"role": "user", "content": "Olá!"}],
        "max_tokens": 256,
    },
)
print(resp.json()["choices"][0]["message"]["content"])
```

### Python (OpenAI SDK)

```python
from openai import OpenAI

client = OpenAI(
    api_key="sk-local-...",
    base_url="http://localhost:18080/v1",
)

response = client.chat.completions.create(
    model="unsloth/gemma-4-E4B-it-GGUF",
    messages=[{"role": "user", "content": "Olá!"}],
)
print(response.choices[0].message.content)
```

### Embeddings

```bash
curl -fsS http://localhost:18080/v1/embeddings \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "default",
    "input": "O que é um appliance de IA local?"
  }' | python3 -m json.tool
```

### Responses API (beta)

```bash
curl -fsS http://localhost:18080/v1/responses \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "unsloth/gemma-4-E4B-it-GGUF",
    "input": "Explique em uma frase."
  }' | python3 -m json.tool
```

## RAG (Busca Semântica)

```bash
# Upload de documento
curl -fsS -X POST http://localhost:18080/client/rag/upload \
  -H "Authorization: Bearer ${API_KEY}" \
  -F "file=@documento.pdf"

# Busca semântica
curl -fsS http://localhost:18080/client/rag/search \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"query": "Qual o prazo de entrega?", "top_k": 3}'
```

## TTS (Text-to-Speech)

```bash
# Gerar áudio
curl -fsS -X POST http://localhost:18080/pocket-tts/tts \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"text": "Olá, esta é uma mensagem de voz do sistema."}' \
  --output audio.wav
```

## Exemplos completos

Consulte a pasta [`examples/`](examples/) para exemplos mais elaborados de integração com chat, embeddings, RAG e TTS.

## Notas

- A API key é gerada pelo admin via Admin Dashboard ou Admin API.
- Para testes rápidos, use `make customer-demo` para criar dados de demonstração.
- Não compartilhe API keys em repositórios públicos ou logs.
