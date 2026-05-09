# LLM Inference Stack API Examples

Este diretório contém exemplos de como utilizar a API do LLM Inference Stack em diferentes linguagens e ferramentas.

## Configuração

Todas as requisições requerem uma API Key de cliente válida. Você pode obter uma API key através do portal do cliente ou via scripts de administração.

### Variáveis de Ambiente

Antes de rodar os exemplos, exporte a sua API Key:

```bash
export CLIENT_API_KEY=sua_api_key_aqui
export BASE_URL=http://localhost:18080
export MODEL=default
```

Se você estiver em um ambiente de desenvolvimento local, você pode carregar as credenciais do cliente de demonstração:

```bash
# Se o arquivo existir
source .local/demo-client.env
export CLIENT_API_KEY=$DEMO_CLIENT_API_KEY
```

## Exemplos cURL

Os scripts cURL estão localizados em `examples/curl/`. Eles requerem o utilitário `jq` para formatar a saída JSON.

```bash
# Dar permissão de execução
chmod +x examples/curl/*.sh

# Listar modelos
./examples/curl/models.sh

# Chat normal
./examples/curl/chat.sh

# Chat com streaming
./examples/curl/streaming.sh

# Responses (simplificado)
./examples/curl/responses.sh
```

## Exemplos Python

Os exemplos Python usam a biblioteca `requests`.

```bash
# Instalar dependências
pip install requests

# Chat normal
python examples/python/chat.py

# Chat com streaming
python examples/python/streaming.py

# Responses (simplificado)
python examples/python/responses.py

# Consulta RAG (requer documentos carregados)
python examples/python/rag_query.py "Qual o conteúdo dos documentos?"
```

## Exemplos Node.js

Os exemplos Node.js usam a API nativa `fetch` (disponível no Node.js 18+).

```bash
# Chat normal
node examples/node/chat.js

# Chat com streaming
node examples/node/streaming.js

# Responses (simplificado)
node examples/node/responses.js

# Consulta RAG (requer documentos carregados)
node examples/node/rag_query.js "Qual o conteúdo dos documentos?"
```

## Endpoints Suportados

- `GET /v1/models`: Lista modelos disponíveis.
- `POST /v1/chat/completions`: Gera respostas de chat (suporta `stream: true`).
- `POST /v1/responses`: Gera respostas via API simplificada (compatibilidade v1.6.0, sem streaming/tools nesta fase).
- `POST /v1/rag/query`: Consulta documentos via RAG.
