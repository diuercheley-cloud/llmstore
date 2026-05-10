# Integração com Open WebUI

O `llm-inference-stack` é compatível com o Open WebUI através da sua API OpenAI-compatible.

## Status de Compatibilidade
- **Status**: Compatível
- **Versão mínima testada**: v0.3.x

## Configuração

### Base URL
Se o Open WebUI estiver rodando no mesmo host (fora do Docker):
`http://localhost:18080/v1`

Se o Open WebUI estiver rodando em Docker (no mesmo host):
`http://host.docker.internal:18080/v1`

### API Key
Utilize qualquer API Key válida gerada pelo sistema (ex: `demo-default`).

### Passo a Passo no Open WebUI
1. Vá em **Settings** > **Connections**.
2. Em **OpenAI API**, adicione uma nova conexão ou edite a existente.
3. Insira a **Base URL** (ex: `http://localhost:18080/v1`).
4. Insira a **API Key**.
5. Clique no ícone de "Refresh" para carregar os modelos.

## Recursos Suportados
- **Chat Completions**: Sim
- **Streaming**: Sim
- **Modelos**: Lista automática via `/v1/models`.

## Limitações
- Embeddings via Open WebUI podem exigir configuração manual se o modelo não for detectado automaticamente.
- Multimodalidade não suportada nesta versão.

## Troubleshooting
- **Conexão recusada**: Verifique se a stack está rodando (`scripts/up.sh`) e se a porta `18080` está acessível.
- **Modelos não aparecem**: Verifique se a API Key tem permissão de acesso aos modelos no control plane.
