---
owner: platform-ops
status: consolidated
---

# Commercial Report Email

Fase 12 adiciona envio opt-in de relatórios executivos comerciais por SMTP seguro, com `disabled` por padrão, `dry_run` seguro, allowlist obrigatória para envio real, auditoria persistida e scanner de segredos antes de qualquer entrega.

## Configuração

```env
COMMERCIAL_REPORT_EMAIL_ENABLED=false
COMMERCIAL_REPORT_EMAIL_MODE=disabled
COMMERCIAL_REPORT_SEND_REAL_EMAIL=false

COMMERCIAL_REPORT_SMTP_HOST=
COMMERCIAL_REPORT_SMTP_PORT=587
COMMERCIAL_REPORT_SMTP_USERNAME=
COMMERCIAL_REPORT_SMTP_PASSWORD=
COMMERCIAL_REPORT_SMTP_FROM=
COMMERCIAL_REPORT_SMTP_USE_TLS=true
COMMERCIAL_REPORT_SMTP_USE_STARTTLS=true
COMMERCIAL_REPORT_SMTP_TIMEOUT_SECONDS=15

COMMERCIAL_REPORT_EMAIL_ALLOWLIST=ops@example.com,finance@example.com
COMMERCIAL_REPORT_EMAIL_MAX_RECIPIENTS=10
COMMERCIAL_REPORT_EMAIL_RETRY_COUNT=3
COMMERCIAL_REPORT_EMAIL_RETRY_BACKOFF_SECONDS=10
```

## Modos

- `disabled`: nenhum envio real. `run-now` retorna `email_disabled`. `send-test-email` retorna `blocked`.
- `dry_run`: valida payload, anexos e destinatários, grava auditoria e retorna `would_send`.
- `smtp`: só envia de verdade quando `COMMERCIAL_REPORT_EMAIL_ENABLED=true`, `COMMERCIAL_REPORT_EMAIL_MODE=smtp` e `COMMERCIAL_REPORT_SEND_REAL_EMAIL=true`.

## SMTP / TLS / STARTTLS

- `COMMERCIAL_REPORT_SMTP_USE_TLS=true` com `COMMERCIAL_REPORT_SMTP_USE_STARTTLS=false` usa `SMTP_SSL`.
- `COMMERCIAL_REPORT_SMTP_USE_STARTTLS=true` usa `SMTP + STARTTLS`.
- Timeout é controlado por `COMMERCIAL_REPORT_SMTP_TIMEOUT_SECONDS`.
- Falhas de autenticação são registradas como `auth_failure`.
- Falhas de TLS são registradas como `tls_failure`.

## Allowlist

- `COMMERCIAL_REPORT_EMAIL_ALLOWLIST` aceita e-mails separados por vírgula.
- Envio real em modo `smtp` é proibido se a allowlist estiver vazia.
- Destinatário fora da allowlist é bloqueado e auditado.
- `COMMERCIAL_REPORT_EMAIL_MAX_RECIPIENTS` limita o total por envio.

## Segurança

- O scanner bloqueia prompts completos, respostas completas, `Authorization`, API keys, provider secrets e payloads brutos.
- Padrões como `sk-*`, `Bearer ...`, `token=...`, `secret=...` e blobs suspeitos são bloqueados.
- O host SMTP é salvo mascarado no log de entrega.
- A senha SMTP nunca entra em logs nem em auditoria.

## Auditoria

Cada tentativa cria um registro em `commercial_report_delivery_logs` com:

- `delivery_status`: `pending`, `dry_run`, `sent`, `failed`, `blocked`
- `delivery_mode`: `disabled`, `dry_run`, `smtp`, `blocked`
- destinatários, assunto, anexos, retries, erro sanitizado e timestamps

O endpoint `GET /admin/routing/executive-dashboard/report-deliveries` resume:

- `sent`
- `dry_run`
- `blocked`
- `failed`
- `retries`
- `auth_failures`
- `tls_failures`
- `blocked_by_security`
- `blocked_by_allowlist`

## Endpoints

- `POST /admin/routing/executive-dashboard/report-schedules/{id}/run-now`
- `POST /admin/routing/executive-dashboard/report-schedules/{id}/send-test-email`
- `GET /admin/routing/executive-dashboard/report-deliveries`

## Troubleshooting

- `blocked_by_allowlist`: confirme allowlist, formato dos e-mails e limite de recipients.
- `blocked_by_security`: o payload ou anexo contém segredo detectado.
- `auth_failure`: valide usuário, senha e política SMTP do servidor.
- `tls_failure`: valide porta, STARTTLS/TLS e certificado do servidor.
- `smtp_network_failure`: valide host, firewall e timeout.

## Riscos e operação

- Nunca habilite `COMMERCIAL_REPORT_SEND_REAL_EMAIL=true` sem testar antes com `dry_run`.
- Mesmo em `dry_run`, o sistema continua offline-friendly e não depende de cloud.
- O relatório exportado por e-mail continua sanitizado e não altera os endpoints OpenAI-compatible.
