---
owner: platform-ops
status: consolidated
---

# Kleber AI SDKs

Facilitando a integração com o stack de inferência Kleber AI.

## Python SDK

Localizado em `sdk/python`.

### Instalação
```bash
pip install -e ./sdk/python
```

### Exemplo Rápido
```python
from kleberai import Client

client = Client(api_key="sua-chave", base_url="http://localhost:18080")
print(client.chat("Olá!"))
```

## Node.js SDK

Localizado em `sdk/node`.

### Instalação e Build
```bash
cd sdk/node
npm install
npm run build
```

### Exemplo Rápido
```javascript
import { Client } from "./sdk/node/dist/index.js";

const client = new Client({ apiKey: "sua-chave" });
const res = await client.chat("Olá!");
console.log(res.choices[0].message.content);
```

## Endpoints Suportados

- `/v1/chat/completions`: Inferência de chat (OpenAI compatível).
- `/v1/models`: Listagem de modelos disponíveis.
- `/v1/embeddings`: Geração de vetores.
- `/client/rag/query`: Consulta RAG inteligente.

## Exemplos Adicionais

Veja a pasta `examples/` para exemplos mais detalhados:
- `examples/python/basic_chat.py`
- `examples/python/rag_query.py`
- `examples/node/basic_chat.js`
