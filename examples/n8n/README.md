# Exemplo n8n

Para integrar o `llm-inference-stack` com o n8n:

1. Importe o workflow de exemplo (se disponível) ou crie um novo.
2. Adicione um nó **OpenAI Chat Model**.
3. Configure as credenciais:
   - **Base URL**: `http://localhost:18080/v1`
   - **API Key**: `demo-default` (ou sua chave real)
4. Use o modelo `unsloth/gemma-4-E4B-it-GGUF`.

## Workflow Típico
`HTTP Trigger` -> `AI Agent` (com OpenAI Chat Model) -> `Respond to Webhook`
