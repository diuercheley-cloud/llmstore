---
owner: platform-ops
status: consolidated
---

# Integração com n8n

O `llm-inference-stack` pode ser utilizado como provedor de LLM em workflows do n8n.

## Status de Compatibilidade
- **Status**: Compatível
- **Nó utilizado**: "OpenAI Chat Model"

## Configuração

### Base URL
`http://localhost:18080/v1`

### API Key
Utilize a API Key gerada no portal do cliente ou via admin.

### Passo a Passo no n8n
1. Adicione um nó **AI Agent** ou **Chain**.
2. No nó de Model, escolha **OpenAI Chat Model**.
3. Crie uma nova credencial:
   - **Resource**: OpenAI
   - **API Key**: Sua chave (ex: `demo-default`)
   - **Base URL**: `http://localhost:18080/v1`
4. No campo **Model**, digite o ID do modelo (ex: `unsloth/gemma-4-E4B-it-GGUF`).

## Recursos Suportados
- **Chat Completions**: Sim
- **Streaming**: Sim (dentro das capacidades do n8n)
- **Embeddings**: Pode ser usado com o nó "OpenAI Embeddings" apontando para a mesma Base URL.

## Limitações
- Funcionalidades específicas de "Tools" do OpenAI podem ter comportamento variado dependendo do backend local utilizado.

## Troubleshooting
- **Timeout**: Workflows do n8n podem ter timeouts curtos. Se o modelo local demorar a responder, aumente o timeout no nó ou no n8n.
