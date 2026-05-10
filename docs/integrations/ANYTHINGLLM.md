# Integração com AnythingLLM

O `llm-inference-stack` pode servir como backend para o AnythingLLM Desktop ou Docker.

## Status de Compatibilidade
- **Status**: Compatível
- **Provedor**: "Generic OpenAI"

## Configuração

### Base URL
`http://localhost:18080/v1`

### API Key
Qualquer chave válida (ex: `demo-default`).

### Passo a Passo no AnythingLLM
1. Vá em **Settings** > **LLM Preference**.
2. Selecione **Generic OpenAI** como provedor.
3. **OpenAI Base URL**: `http://localhost:18080/v1`
4. **API Key**: Sua chave.
5. **Token limit**: Ajuste conforme o plano (ex: 4096).
6. Salve e selecione o modelo na lista suspensa.

## Recursos Suportados
- **Chat Completions**: Sim
- **Streaming**: Sim
- **Embeddings**: Pode ser configurado separadamente em "Embedding Preference" usando também "Generic OpenAI".

## Limitações
- O AnythingLLM pode tentar validar a chave contra os servidores da OpenAI se o provedor não for configurado corretamente como "Generic".

## Troubleshooting
- Se o AnythingLLM estiver em Docker, use `http://host.docker.internal:18080/v1` como Base URL.
