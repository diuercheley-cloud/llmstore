# Commercial Report Export

Fase 11 adiciona exportação do relatório executivo comercial em `json`, `csv` e `html`, com `pdf` opcional quando uma dependência compatível estiver instalada. Também adiciona schedules `monthly|weekly` com execução segura em modo `disabled` ou `dry_run` por padrão.

## Formatos

- `json`: payload estruturado e sanitizado.
- `csv`: resumo executivo em linha única para ingestão e planilha.
- `html`: relatório imprimível.
- `pdf`: opcional. Retorna `501` quando não houver engine segura disponível.

## Endpoints

- `GET /admin/routing/executive-dashboard/export?format=json|csv|html|pdf&hours=24`
- `GET /admin/routing/executive-dashboard/export/preview?hours=24`
- `GET /admin/routing/executive-dashboard/report-schedules`
- `POST /admin/routing/executive-dashboard/report-schedules`
- `POST /admin/routing/executive-dashboard/report-schedules/{id}/run-now`
- `POST /admin/routing/executive-dashboard/report-schedules/{id}/disable`
- `POST /admin/routing/executive-dashboard/report-schedules/{id}/enable`

## Curl

```bash
curl -sS \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  "http://localhost:8080/admin/routing/executive-dashboard/export?format=json&hours=24"
```

```bash
curl -sS \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  "http://localhost:8080/admin/routing/executive-dashboard/export?format=html&hours=24" \
  -o executive-report.html
```

```bash
curl -sS \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -X POST \
  "http://localhost:8080/admin/routing/executive-dashboard/report-schedules" \
  -d '{
    "name": "Monthly Executive Report",
    "frequency": "monthly",
    "day_of_month": 1,
    "hour_utc": 8,
    "format": "html",
    "recipients_json": ["ops@example.com"],
    "filters_json": {"hours": 24}
  }'
```

## HTML Imprimivel

Use `format=html` ou o endpoint `/preview`. O HTML foi desenhado para abrir localmente e imprimir sem dependência externa.

## PDF Opcional

O serviço tenta usar uma engine Python suportada apenas se ela já estiver instalada. Sem isso, responde `501` com mensagem clara e orientação para usar HTML.

## Schedule Mensal

- `monthly`: usa `day_of_month` entre `1` e `28`.
- `weekly`: usa `day_of_week` entre `0` e `6`.
- `next_run_at` é recalculado ao criar, habilitar e executar.
- O scheduler interno verifica schedules vencidos a cada hora.

## Email

Configurações:

- `COMMERCIAL_REPORT_EMAIL_ENABLED=false`
- `COMMERCIAL_REPORT_EMAIL_MODE=disabled`
- `COMMERCIAL_REPORT_EMAIL_PROVIDER=disabled`
- `COMMERCIAL_REPORT_DEFAULT_RECIPIENTS=`
- `COMMERCIAL_REPORT_SEND_REAL_EMAIL=false`

Comportamento:

- `disabled`: `run-now` gera o relatório e retorna `email_disabled`.
- `dry_run`: `run-now` retorna `would_send`.
- envio real nunca acontece sem `COMMERCIAL_REPORT_SEND_REAL_EMAIL=true`.

## Seguranca E Sanitizacao

- API keys, `Authorization`, provider secrets, prompts completos, respostas completas e payloads brutos não entram no relatório.
- `sanitize_report_payload(...)` redige chaves proibidas e bloqueia export se detectar padrões de secrets.
- O scanner roda antes do JSON/CSV/HTML/PDF.

## Troubleshooting

- `501` em PDF: usar `format=html`.
- `400` por scanner: revisar origem do payload administrativo e remover conteúdo sensível.
- schedule não executa: validar `enabled=true`, `next_run_at` e relógio UTC.
