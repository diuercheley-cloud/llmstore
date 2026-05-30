# Mobile Foundation

A base para aplicativos mobile (iOS e Android) no Control Plane permite que dispositivos sejam registrados, sessões mobile sejam mantidas e notificações push sejam enviadas aos usuários.

## Recursos Disponíveis

- **Device Registry**: Registro unificado de dispositivos com tokens de push (FCM/APNs).
- **Mobile Sessions**: Sessões de longa duração (30 dias por padrão) com tokens seguros.
- **Activity Feed**: Endpoint otimizado para exibir as últimas atividades do tenant no app.
- **Push Notification Framework**: Infraestrutura pronta para disparar alertas sobre execuções de agentes ou eventos de sistema.

## Configuração

Habilite o suporte mobile no arquivo `.env`:

```env
MOBILE_FOUNDATION_ENABLED=true
PUSH_NOTIFICATIONS_ENABLED=true
```

## Arquitetura de Sessão

Diferente das sessões web que expiram rapidamente, as sessões mobile utilizam um `session_token` persistido no dispositivo. O token é vinculado a um `device_id` específico, garantindo que o roubo de um token não permita acesso via outros dispositivos.

## Feed de Atividades

O endpoint `GET /v1/mobile/feed` consolida eventos relevantes para o usuário mobile, como:
- Conclusão de `AgentRuns`.
- Novas mensagens em canais colaborativos.
- Alertas de quota ou billing.
