---
owner: platform-ops
status: consolidated
---

# Commercial Revenue Escalations

Revenue Protection Escalations adiciona um plano de notificacao para eventos financeiros/comerciais criticos sem habilitar integracoes reais por padrao.

## Flow

1. Um evento elegivel e gerado por `anomaly`, `policy_action`, `forecast`, `reconciliation` ou `dispute`.
2. O payload e construido por `build_alert_payload(...)`.
3. O payload passa por `sanitize_alert_payload(...)`.
4. As policies de escalacao sao avaliadas por severidade, trigger e ordem de entrega.
5. O sistema aplica `dedupe_key`, `payload_hash` e cooldown.
6. Cada tentativa gera um registro em `commercial_revenue_alert_deliveries`.

## Integrations

- Slack: webhook simples com `severity`, `source_type`, `summary`, `recommendation` e `timestamp`.
- PagerDuty: evento minimo via Events API v2, sem SDK pesada.
- Webhook outbound: HMAC SHA256 em `X-Commercial-Revenue-Signature`.
- Email escalation: reutiliza o SMTP seguro da Fase 12 e respeita allowlist.

## Modes

- `disabled`: entrega suprimida.
- `dry_run`: registra a entrega como `dry_run` sem chamada real.
- `enabled`: faz tentativa real somente nos canais explicitamente habilitados.

## Security

- Nenhum canal real vem habilitado por default.
- Secrets e URLs sensiveis sao mascarados nos destinos persistidos.
- `prompt`, `response`, `token`, `secret`, `routing_key` e similares sao redigidos.
- Credenciais SMTP, Slack, PagerDuty e webhook secret nao sao logadas.

## Cooldown, Dedupe, Retry

- `dedupe_key`: evita reenvio idempotente do mesmo evento por canal.
- `payload_hash`: diferencia payload identico de payload alterado para o mesmo evento.
- cooldown: payload alterado no mesmo periodo entra como `suppressed`.
- retry/backoff: `apply_retry_backoff(...)` usa backoff exponencial controlado.
- manual retry: `POST /admin/billing/revenue-escalations/retry/{id}` respeita limite de tentativas.

## Trigger Coverage

- critical anomalies
- repeated mismatches
- mass disputes
- margin collapse
- repeated safe_mode activations
- failed revenue protection actions

## Risks

- O retry automatico e propositalmente curto; operacao humana continua relevante para incidentes externos prolongados.
- O webhook outbound depende de `COMMERCIAL_REVENUE_WEBHOOK_SIGNING_SECRET`; sem secret o canal fica suprimido.
- Forecast ainda nao gera escalations automaticas nesta fase; o suporte esta pronto no modelo/policy.
