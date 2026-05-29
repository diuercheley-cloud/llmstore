---
owner: platform-ops
status: consolidated
---

# SDK de Adapters Agentic

O SDK do KleberAI fornece as classes base e tipos necessários para construir extensões compatíveis com o ecossistema agentic.

## Instalação

### Python
```bash
pip install kleberai-sdk
```

### Node.js
```bash
npm install @kleberai/sdk
```

## Criando um Tool Adapter (Python)

```python
from kleberai.agents.adapters import ToolAdapterV1, AdapterManifest

class MyCustomTool(ToolAdapterV1):
    async def manifest(self):
        return AdapterManifest(
            id="my-tool",
            name="My Tool",
            version="1.0.0",
            compatibility_version="v1",
            permissions=["network.access"]
        )

    async def execute(self, tool_input, context):
        # Lógica da ferramenta
        return {"status": "done"}
```

## Criando um Memory Provider (Node.js)

```typescript
import { MemoryProviderV1, AdapterManifest } from '@kleberai/sdk';

class RedisMemory extends MemoryProviderV1 {
  async manifest(): Promise<AdapterManifest> {
    return {
      id: 'redis-memory',
      name: 'Redis Memory',
      version: '1.2.0',
      compatibility_version: 'v1',
      metadata: {},
      permissions: ['storage.write']
    };
  }

  async store(agentId: string, runId: string, item: any): Promise<boolean> {
    // Persistência no Redis
    return true;
  }
}
```

## Validação e Testes

O SDK inclui utilitários para validar a compatibilidade do seu adapter antes do deploy:

```bash
kleber-sdk validate ./my_adapter.py
```
