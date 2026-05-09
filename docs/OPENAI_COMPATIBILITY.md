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

## Configuração de Embeddings

No arquivo `.env`:
```env
EMBEDDINGS_ENABLED=true
EMBEDDINGS_BACKEND=mock
DEFAULT_EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=384
```

## Limites e Cotas

Os embeddings possuem limites separados de tokens de chat nos planos de faturamento:
- **Embeddings Enabled**: Ativa/Desativa o recurso para o cliente.
- **Requests per Month**: Limite de chamadas ao endpoint.
- **Tokens per Month**: Limite de tokens processados (estimados: 4 chars = 1 token).
- **Max Inputs per Request**: Máximo de strings em um array por chamada.
