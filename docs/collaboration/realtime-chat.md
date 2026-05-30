# Real-time Collaborative Chat

O Collaborative Chat permite que usuários e agentes interajam em canais compartilhados, facilitando a automação de processos e o suporte multiusuário.

## Recursos Principais

- **Canais por Tenant**: Isolamento total de conversas entre diferentes organizações.
- **WebSocket**: Mensagens entregues em tempo real.
- **Agent Mentions**: Marque um agente com `@[agent-uuid]` para disparar uma execução e receber a resposta diretamente no canal.
- **Presence**: Veja quem está online no sistema.

## Configuração

Habilite o recurso no arquivo `.env`:

```env
COLLAB_CHAT_ENABLED=true
COLLAB_CHAT_WEBSOCKET_ENABLED=true
```

## API Endpoints

- `GET /v1/chat/channels`: Lista canais disponíveis.
- `POST /v1/chat/channels`: Cria um novo canal.
- `GET /v1/chat/channels/{id}/messages`: Recupera o histórico de mensagens.
- `POST /v1/chat/channels/{id}/messages`: Envia uma nova mensagem.
- `WS /v1/chat/channels/{id}/stream`: Conecta ao stream de eventos em tempo real.

## Integração com Agentes

Qualquer agente pode ser adicionado como participante de um canal. Quando mencionado, o Control Plane cria um `AgentRun`, processa a solicitação e publica a resposta como uma mensagem do tipo `agent_response`.
