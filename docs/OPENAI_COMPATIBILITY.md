# OpenAI API Compatibility

A llm-inference-stack visa oferecer alta compatibilidade com a API da OpenAI para facilitar a migração de aplicações existentes e integração com ferramentas do ecossistema (como LangChain, LlamaIndex, etc.).

## Endpoints Suportados

### Chat Completions (`/v1/chat/completions`)
- **Status**: Totalmente Suportado (Local)
- **Modelos**: Qualquer modelo GGUF ou via Ollama/LMStudio.
- **Recursos**: Streaming, Mensagens do Sistema, Ferramentas (via backend que suporte), Reasoning (O1 style).

### Responses (`/v1/responses`) - NOVO v1.6.0
- **Status**: Suporte Básico (Local)
- **Descrição**: Camada de compatibilidade simplificada sobre Chat Completions.
- **Recursos**:
    - Input como string ou array simples de strings/mensagens textuais.
    - `instructions` mapeado para `system message`.
    - Resposta estruturada com `created_at`, `status`, `output` e `output_text`.
    - `usage` e billing local/manual reaproveitam a trilha de chat com endpoint registrado como `/v1/responses`.
    - Headers de compatibilidade: `X-Requested-Model`, `X-Resolved-Model`, `X-Backend-Name`, `X-Fallback-Used`.
- **Limitações**:
    - Streaming ainda não é executado; retorna `501` com `error.code = responses_streaming`.
    - `tools` e `tool_choice` não são executados; retornam `501` com `error.code = responses_tools_unsupported`.
    - Sem suporte multimodal neste endpoint. Apenas conteúdo textual simplificado.

### Embeddings (`/v1/embeddings`) - NOVO v1.6.0
- **Status**: Suportado (Mock Determinístico / Futuro Local Real)
- **Modelos**: `text-embedding-3-small` (default mock).
- **Recursos**:
    - Input como string única ou array de strings.
    - Dimensões configuráveis (padrão 384).
    - Comportamento determinístico (mesmo input gera mesmo vetor).
    - Gestão de cotas e limites por plano.

### Models (`/v1/models`)
- **Status**: Suportado
- **Descrição**: Lista modelos de chat e agora modelos de embedding ativos.

## Integrações com Ferramentas Externas

A stack foi validada e possui guias de configuração para as seguintes ferramentas:

- [Open WebUI](integrations/OPEN_WEBUI.md)
- [n8n](integrations/N8N.md)
- [LangChain](integrations/LANGCHAIN.md)
- [AnythingLLM](integrations/ANYTHINGLLM.md)

Para qualquer outra ferramenta que suporte OpenAI, utilize a Base URL `http://localhost:18080/v1` e uma API Key gerada no sistema.

## Configuração de Embeddings

No arquivo `.env`:
```env
EMBEDDINGS_ENABLED=true
EMBEDDINGS_BACKEND=mock
DEFAULT_EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=384
```

## Limites e Cotas

Os limites são aplicados conforme o Plano Comercial associado ao cliente:
- **RPM / RPD**: Limite de requisições por minuto e por dia.
- **Monthly Token Quota**: Limite de tokens acumulados no mês.
- **Max Context Tokens**: Limite de tokens de entrada (Prompt + History).
- **Feature Gates**: Bloqueio de RAG, TTS, Embeddings ou Responses caso não permitidos no plano (ex: Plano Free possui RAG desabilitado).
- **Model Access**: Restrição de quais modelos podem ser chamados.

## Matriz de Capacidades

O sistema expõe uma matriz detalhada do que é mock, local real ou production-ready em `docs/CAPABILITY_MATRIX.md`.

Administradores podem consultar as capacidades programaticamente via:
`GET /admin/capabilities` (requer `X-Admin-Token`).

## Capabilities no Metadata do Modelo

O endpoint `/v1/models` inclui agora um campo `capabilities` dentro de `metadata` para cada modelo, indicando suporte a:
- `supports_chat` (boolean)
- `supports_streaming` (boolean)
- `supports_embeddings` (boolean)
- `supports_responses` (boolean)
- `supports_tools` (boolean)
