---
owner: platform-ops
status: consolidated
---

# Function Calling

O stack agora aceita payloads compatíveis com OpenAI para function calling em:

- `POST /v1/chat/completions`
- `POST /v1/responses`

Campos aceitos:

- `tools`
- `tool_choice`
- `parallel_tool_calls`
- `response_format`

## Comportamento

- Modelos `openai_compatible` recebem o payload de tools em formato OpenAI nativo.
- Modelos `llama.cpp` e `openai_compatible` recebem o payload de tools em formato OpenAI nativo.
- Providers sem suporte nativo (`ollama`, `vllm`) retornam `501` com `error.code=capability_not_supported`.
- `/v1/responses` continua sem streaming; quando há tool call, o output inclui item `type=function_call`.

## Validacao

Validacoes locais aplicadas antes de encaminhar ao provider:

- Nome da funcao: `^[A-Za-z0-9_-]{1,64}$`
- Maximo de `16` tools por request
- Schema maximo por tool: `24 KiB`
- Profundidade maxima de schema: `8`
- Maximo de `256` propriedades por schema
- Keywords bloqueadas por seguranca: `$ref`, `$defs`, `definitions`, `allOf`, `oneOf`, `not`, `if`, `then`, `else`, `dependentSchemas`, `patternProperties`, `unevaluatedProperties`, `contentEncoding`, `contentMediaType`
- Argumentos de tool retornados pelo provider: maximo de `16 KiB`

## Logs e Billing

- Billing e tokens seguem o fluxo normal.
- `RequestLog` grava `tool_call_count`.
- `RequestLog` grava apenas preview sanitizado dos tool calls.
- Argumentos completos nao sao persistidos por padrao no admin nem nos exports.

## Exemplo: `/v1/chat/completions`

```bash
curl -s http://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "default",
    "messages": [
      {"role": "user", "content": "Como esta o clima em Campinas?"}
    ],
    "tools": [
      {
        "type": "function",
        "function": {
          "name": "weather_mock",
          "description": "Retorna clima mockado",
          "parameters": {
            "type": "object",
            "properties": {
              "city": {"type": "string"}
            },
            "required": ["city"]
          }
        }
      }
    ],
    "tool_choice": "auto",
    "parallel_tool_calls": false
  }'
```

Resposta esperada quando o provider retorna tool call:

```json
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": null,
        "tool_calls": [
          {
            "id": "call_weather_1",
            "type": "function",
            "function": {
              "name": "weather_mock",
              "arguments": "{\"city\":\"Campinas\"}"
            }
          }
        ]
      },
      "finish_reason": "tool_calls"
    }
  ]
}
```

## Exemplo: `/v1/responses`

```bash
curl -s http://localhost:8080/v1/responses \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "default",
    "input": "Como esta o clima em Campinas?",
    "tools": [
      {
        "type": "function",
        "function": {
          "name": "weather_mock",
          "parameters": {
            "type": "object",
            "properties": {
              "city": {"type": "string"}
            }
          }
        }
      }
    ],
    "tool_choice": "auto"
  }'
```

Resposta esperada:

```json
{
  "object": "response",
  "output": [
    {
      "type": "function_call",
      "name": "weather_mock",
      "arguments": "{\"city\":\"Campinas\"}",
      "call_id": "call_weather_1"
    }
  ],
  "output_text": ""
}
```

## Limitacoes

- Streaming estruturado de tool call em `/v1/responses` ainda nao existe.
- Para providers locais sem suporte nativo, o stack nao executa fallback automatico de tools localmente.
- O stack valida e repassa tools; nao executa a funcao em nome do cliente.
