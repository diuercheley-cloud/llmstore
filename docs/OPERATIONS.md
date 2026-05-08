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
./scripts/up.sh
```

Validar saúde:

```bash
./scripts/test-health.sh
```

Executar validação completa:

```bash
./scripts/validate-e2e.sh
```

## Backup e restore

Backup:

```bash
./scripts/backup.sh
```

O backup completo inclui:

- dump do PostgreSQL
- cópia local do arquivo de ambiente com permissão preservada
- `VERSION`
- `docker-compose*.yml`
- `models.manifest.json` sem copiar os blobs `.gguf` por padrão
- `checksums.sha256`

Restore:

```bash
./scripts/restore.sh /caminho/para/backup-dir
```

O restore valida `VERSION`, revisão de schema (`alembic`), checksums e exige confirmação explícita. O `.env.local` só é sobrescrito se você confirmar.

Teste de disaster recovery:

```bash
./scripts/dr-test.sh /caminho/para/backup-dir
```

O script sobe uma stack temporária isolada, restaura o backup, valida `health` e `ready`, roda um chat de teste e grava um relatório em `artifacts/dr-tests/`.

## Experiência de Produção Local

Para testar o stack como se estivesse em um ambiente de produção real (com landing page, pricing e portal amigável):

```bash
./scripts/local-production-up.sh
```

Este script configura a stack, garante que o cliente `demo-client` exista e gera um resumo em `artifacts/local-production/`.

### Saúde da UI
```bash
./scripts/ui-health.sh
```

### Smoke Test Completo
```bash
./scripts/local-production-smoke.sh [SUA_API_KEY]
```

### Circuit Breaker

Reset explícito do circuit breaker do data plane:

```bash
./scripts/reset-circuit-breaker.sh
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
./scripts/create-plan.sh business-local "Business Local"
```

Criar cliente:

```bash
./scripts/create-client.sh cliente-acme "tenant comercial"
```

Criar cliente demo com portal:

```bash
./scripts/create-customer-demo.sh cliente-demo "cliente piloto" basic
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
./scripts/expose-local.sh
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
./scripts/reset-dev.sh
```

O script pede confirmação antes de remover volumes, artefatos e opcionalmente `.env` e modelos.
