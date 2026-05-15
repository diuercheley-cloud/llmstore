# Kleber AI Python SDK

Minimal SDK for Kleber AI.

## Instalação

```bash
pip install -e .
```

## Uso

```python
from kleberai import Client

client = Client(api_key="your-api-key", base_url="http://localhost:18080")

# Chat
response = client.chat("Explique esse erro")
print(response["choices"][0]["message"]["content"])

# Listar modelos
models = client.models()
print(models)

# Embeddings
emb = client.embeddings("texto")
print(emb)
```
