# Kleber AI Python SDK

Python SDK for interacting with the Kleber AI Agentic Platform.

## Instalação

```bash
pip install kleberai
```

## Autenticação

O SDK requer uma chave de API para a maioria das operações. Você pode passá-la diretamente para o cliente ou definir a variável de ambiente `KLEBERAI_API_KEY`.

```python
from kleberai import Client

client = Client(api_key="your-api-key")
```

## Exemplos Básicos

### Chat Completions

```python
from kleberai import Client

client = Client()
response = client.chat("Olá, como você pode me ajudar hoje?")
print(response["choices"][0]["message"]["content"])
```

### Gerenciamento de Agentes

```python
agents = client.agents.list()
for agent in agents:
    print(f"Agent: {agent.name} (ID: {agent.id})")
```

### RAG (Retrieval Augmented Generation)

```python
# Upload de documento
client.rag.upload_document("knowledge.pdf", collection_id="my-docs")

# Busca semântica
results = client.rag.search("O que é Kleber AI?", collection_id="my-docs")
```

## Compatibilidade

| Versão SDK | Versão API Mínima |
| ---------- | ----------------- |
| 0.2.x      | 2.0.0             |
| 0.1.x      | 1.8.0             |

## Desenvolvimento

```bash
git clone https://github.com/kleber/llm-inference-stack.git
cd sdk/python
pip install -e ".[dev]"
pytest
```
