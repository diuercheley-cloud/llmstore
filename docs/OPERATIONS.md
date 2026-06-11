---
owner: platform-ops
status: consolidated
---

# Operations

## Comandos principais

```bash
make install
make up
make down
make validate
make backup
make logs
```

## Fluxo diário

Subir a stack:

```bash
./scripts/deploy/up.sh
```

Validar saúde:

```bash
./scripts/dev/test-health.sh
```

Executar validação completa:

```bash
./scripts/validators/validate-e2e.sh
```

## Backup e restore

Backup:

```bash
llmstack backup --logical-agent-backup
```

O backup lógico de agentes inclui:

- banco lógico dos componentes suportados
- configs (config/*.yml, config/*.yaml, VERSION. Nota: .env e .env.local são excluídos por segurança)
- feature flags
- agentes
- workflows
- embeddings metadata
- criptografia do payload
- assinatura HMAC-SHA256
- checksum SHA-256 do pacote
- verificação automática após criação

Restore:

```bash
llmstack restore BACKUP_ID --dry-run
llmstack restore BACKUP_ID --yes
```

O restore valida assinatura, checksum e hashes de cada componente antes de aplicar qualquer mudança. Se a verificação falhar, o restore fica bloqueado.
O restore real também exige confirmação explícita com `--yes`.

Dashboard:

- Admin Dashboard: `/admin-dashboard/operations/backups`
- Fluxos disponíveis: criar backup full, verificar integridade, simular restore e executar restore

Monitoramento e Métricas Prometheus:

O endpoint `/metrics` expõe as seguintes métricas operacionais para Backup e Restore:
- `backup_last_success_timestamp`: Unix timestamp do último backup bem-sucedido.
- `backup_age_seconds`: Tempo em segundos desde o último backup bem-sucedido.
- `backup_size_bytes`: Tamanho do último backup bem-sucedido em bytes.
- `backup_failure_total`: Contador total de falhas na criação de backup.
- `restore_failure_total`: Contador total de falhas na restauração de backup.
- `backup_duration_seconds`: Histograma de duração das operações de backup.
- `restore_duration_seconds`: Histograma de duração das operações de restore.
- `estimated_rpo_seconds`: RPO estimado com base na idade do último backup bem-sucedido.
- `measured_rto_seconds`: RTO medido a partir da duração da última restauração bem-sucedida.

Alertas sugeridos para Alertmanager/Prometheus:

```yaml
groups:
  - name: DisasterRecoveryAlerts
    rules:
      - alert: BackupStale
        expr: backup_age_seconds > 86400
        for: 15m
        labels:
          severity: critical
        annotations:
          summary: "Backup stale for more than 24 hours"
          description: "No successful backup has been recorded in the last 24 hours."

      - alert: BackupFailureDetected
        expr: rate(backup_failure_total[10m]) > 0
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "Backup failures detected"
          description: "Multiple backup operations have failed in the last 10 minutes."

      - alert: RestoreFailureDetected
        expr: rate(restore_failure_total[10m]) > 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Restore failures detected"
          description: "Restore or rollback operations have failed in the last 10 minutes."
```

Teste de disaster recovery:

```bash
python3 -m pytest tests/api/test_admin_backup.py -q
```

Cobertura atual:

- backup
- restore
- integridade
- corrupção

## Experiência de Produção Local

Para testar o stack como se estivesse em um ambiente de produção real (com landing page, pricing e portal amigável):

```bash
./scripts/dev/local-production-up.sh
```

Este script configura a stack, garante que o cliente `demo-client` exista e gera um resumo em `artifacts/local-production/`.

### Saúde da UI
```bash
./scripts/dev/ui-health.sh
```

### Smoke Test Completo
```bash
./scripts/validators/local-production-smoke.sh [SUA_API_KEY]
```

### Circuit Breaker

Reset explícito do circuit breaker do data plane:

```bash
./scripts/dev/reset-circuit-breaker.sh
```

O circuit breaker fica em memória dentro do processo `control-plane`. Reiniciar o container `control-plane` também limpa esse estado.

## Segurança e Hardening Local

### Checagem de Secrets
Para evitar o vazamento acidental de tokens e chaves no repositório, utilize o script de checagem:

```bash
make check-secrets
```

O script procura por padrões de API keys, tokens administrativos e chaves privadas, ignorando arquivos de exemplo e diretórios de build/modelos.

### Instalação de Git Hooks
Recomendamos a instalação do pre-commit hook para checagem automática de secrets antes de cada commit:

```bash
make install-git-hooks
```

Isso configurará o Git para usar os hooks localizados em `.githooks/`. Você também pode configurar manualmente:
```bash
git config core.hooksPath .githooks
```

## Operação comercial

Criar plano:

```bash
./scripts/dev/create-plan.sh business-local "Business Local"
```

Criar cliente:

```bash
./scripts/dev/create-client.sh cliente-acme "tenant comercial"
```

Criar cliente demo com portal:

```bash
./scripts/dev/create-customer-demo.sh cliente-demo "cliente piloto" basic
```

## Portais

- Admin: `/admin-dashboard`
- Admin Lab: `/admin-lab` (Laboratório financeiro e operacional)
- Cliente: `/client-portal`

Nunca use `X-Admin-Token` no portal do cliente.
Se `PUBLIC_EXPOSURE=true`, os endpoints `/admin-dashboard` e `/admin-lab` ficam desabilitados por segurança.

## Gerenciamento de modelos pelo Admin Lab

Use `/admin-lab`, aba `Modelos`, para operar o registro de LLMs sem shell:

- copie o arquivo `.gguf` para `./models`
- valide se ele apareceu em `GET /admin/models/files`
- registre o modelo pela UI com alias, `model_id`, provider, backend e contexto
- teste o prompt antes de expor o modelo a clientes
- use enable/disable e set-default pela UI
- remova o registro com segurança; o arquivo `.gguf` não é apagado

Guardrails:

- caminhos fora de `/models` são bloqueados
- `llama.cpp` exige extensão `.gguf`
- alias e `model_id` duplicados são rejeitados
- modelo default não pode ser removido nem desabilitado
- ações Docker de backend dependem de `TEST_TOOLS_ENABLED=true` e `PUBLIC_EXPOSURE=false`

Limitação conhecida:

- esta versão não gera `docker-compose.yml` arbitrário nem cria containers novos fora dos serviços já conhecidos do compose

## Exposição Externa Segura

Para expor o `llm-inference-stack` para a internet com segurança:

1. **Ative PUBLIC_API_ENABLED:** Defina como `true` no `.env.local` para habilitar proteções adicionais e limites globais.
2. **Use HTTPS:** Nunca exponha o stack sem TLS. Recomendamos Cloudflare Tunnels ou Nginx com certbot.
3. **Configure Rate Limits:** Ajuste os limites de plano e limites globais de IP no `control_plane/app/services/rate_limit.py`.
4. **IP Allowlist:** Use o recurso de IP Allowlist por cliente (via admin API) para restringir o acesso apenas a IPs conhecidos.
5. **Monitoramento:** Acompanhe os logs de auditoria e métricas do Prometheus para identificar picos de tráfego suspeitos.

### Teste Rápido (Tunnel Local)

Você pode usar o script auxiliar:
```bash
./scripts/dev/expose-local.sh
```

### Riscos
- **Abuso de VRAM:** Requisições simultâneas massivas podem causar OOM na GPU se não houver fallback configurado.
- **Custo:** Se estiver usando backends pagos (como OpenAI fallback), monitore o consumo de tokens.
- **Exposição de Dashboard Admin:** O dashboard admin deve ser protegido por firewall ou VPN, nunca exposto diretamente.

## Rotação de credenciais

Rotacionar API key de cliente:

```bash
curl -fsS -X POST http://localhost:18080/admin/api-keys/UUID_DA_KEY/rotate \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" | python3 -m json.tool
```

A resposta traz a nova chave em plaintext uma única vez e revoga a anterior.

## Otimização de Inferência e Diagnóstico

### Gestão de Contexto
O control-plane agora gerencia ativamente o contexto enviado ao data-plane para garantir estabilidade e foco, especialmente para modelos locais pequenos.

As variáveis de controle são:
- `INFERENCE_MAX_CONTEXT_TOKENS` (default 4096)
- `INFERENCE_MAX_COMPLETION_TOKENS` (default 512)
- `INFERENCE_MAX_SYSTEM_CHARS` (default 2500)
- `INFERENCE_MAX_HISTORY_MESSAGES` (default 8)

### Diagnóstico de Logs
Sempre que uma request de chat é processada, um log estruturado é gerado com a tag `Inference context optimized`. Você pode consultar métricas de truncamento:

```bash
docker compose logs control-plane | grep "Inference context optimized"
```

O log contém:
- `original_message_count` vs `final_message_count`
- `estimated_context_tokens_before` vs `after`
- `max_tokens_before` vs `after` (capping)
- `truncated`: boolean indicando se houve corte de histórico ou system prompt.

### Defaults para Modelos Locais
Para backends `llama.cpp` e `ollama`, o sistema aplica automaticamente `temperature: 0.4` e `top_p: 0.9` se o cliente não enviar valores específicos. Isso evita instabilidade em tarefas de instrução.

Rotacionar `ADMIN_TOKEN`:

1. editar `.env.local`
2. substituir `ADMIN_TOKEN` por um valor forte
3. confirmar `chmod 600 .env.local`
4. reiniciar a stack com `docker compose up -d`

## Limpeza de ambiente local

```bash
./scripts/dev/reset-dev.sh
```

O script pede confirmação antes de remover volumes, artefatos e opcionalmente `.env` e modelos.
