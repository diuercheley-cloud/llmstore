# Mobile API Reference

Documentação técnica dos endpoints dedicados para integração com apps nativos.

## Endpoints Principais

### Registrar Dispositivo
- **URL**: `POST /v1/mobile/devices`
- **Payload**:
  ```json
  {
    "device_token": "FCM_TOKEN_HERE",
    "platform": "ios",
    "model": "iPhone 15 Pro",
    "app_version": "1.0.0"
  }
  ```

### Iniciar Sessão Mobile
- **URL**: `POST /v1/mobile/sessions`
- **Payload**:
  ```json
  {
    "device_token": "FCM_TOKEN_HERE"
  }
  ```
- **Resposta**: `200 OK` com `session_token` e `expires_at`.

### Feed de Atividades
- **URL**: `GET /v1/mobile/feed`
- **Resposta**: Lista de eventos ordenados por data decrescente.

### Testar Notificação Push
- **URL**: `POST /v1/mobile/push/test`
- **Descrição**: Dispara uma notificação de teste para todos os dispositivos ativos do usuário logado.
