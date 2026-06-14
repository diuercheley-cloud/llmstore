# Real-time Voice Foundation

O Control Plane fornece uma base para conversações de voz em tempo real com agentes, suportando streaming de áudio bidirecional.

## Surface Status

- `POST /v1/voice/sessions`: `beta`
- `GET /v1/voice/sessions`: `beta`
- `GET /v1/voice/sessions/{session_id}`: `beta`
- `DELETE /v1/voice/sessions/{session_id}`: `beta`
- `POST /v1/voice/webrtc/offer`: `simulated`

As sessões de voz e o streaming WebSocket usam serviços reais de sessão, STT/TTS e persistência. O endpoint WebRTC ainda responde com um SDP placeholder e não deve ser tratado como signaling de produção.

## Configuração

Habilite o recurso no arquivo `.env`:

```env
REALTIME_VOICE_ENABLED=true
```

## Arquitetura de Voz

O fluxo de voz funciona da seguinte forma:

1. **User Audio -> STT**: O áudio do usuário é enviado via WebSocket e convertido em texto (STT).
2. **Turn Detection**: O sistema detecta quando o usuário terminou de falar (VAD/Turn Detection).
3. **Agent Logic**: O texto transcrito é enviado ao agente.
4. **Agent Response -> TTS**: A resposta do agente é convertida em áudio (TTS).
5. **TTS -> User Audio**: O áudio resultante é enviado de volta ao usuário via WebSocket.

## Endpoints

- `POST /v1/voice/sessions`: Inicia uma nova sessão de voz com um agente.
- `GET /v1/voice/sessions`: Lista sessões existentes do tenant autenticado.
- `GET /v1/voice/sessions/{session_id}`: Recupera metadados de uma sessão.
- `DELETE /v1/voice/sessions/{session_id}`: Encerra uma sessão.
- `POST /v1/voice/webrtc/offer`: Simula o handshake WebRTC atual.
- `WS /v1/voice/sessions/{id}/stream`: Stream de áudio e eventos em tempo real.

## Privacidade

Por padrão, o áudio bruto dos usuários **não é armazenado**. Apenas as transcrições das conversas são persistidas para fins de histórico e contexto do agente.
