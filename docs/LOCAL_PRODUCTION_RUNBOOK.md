# Local Production Runbook

Este documento descreve como operar o sistema `llm-inference-stack` em ambiente local (`localhost`) com todas as funcionalidades da camada SaaS habilitadas.

## 1. Visão Geral

O modo `local-production` simula o comportamento de um ambiente de produção completo, incluindo landing page, pricing, portal do cliente e admin dashboard, mas rodando inteiramente na sua máquina.

- **Base URL padrão:** `http://localhost:18080`
- **Escopo:**
    - Autenticação e API Keys
    - Gestão de Clientes e Planos
    - Inferência de LLM (OpenAI-compatible)
    - RAG Local (Upload e Query)
    - Billing Manual (Simulação de faturas e pagamentos)
    - Observabilidade (Métricas e Dashboards)
- **Fora de Escopo:**
    - Gateway de pagamento real (PSP)
    - Pagamentos PIX real (apenas simulação manual)
    - Domínio público (acesso apenas via localhost)
    - HTTPS obrigatório (uso de HTTP em localhost)

## 2. Pré-requisitos

Certifique-se de ter as seguintes ferramentas instaladas:

- **Docker & Docker Compose:** Recomendado Docker Desktop com integração WSL2 no Windows.
- **Python 3.10+:** Com `venv` para scripts auxiliares e testes.
- **Ferramentas de CLI:** `curl`, `jq`, `git`, `make`.
- **WSL2 (Windows):** Necessário para melhor performance de GPU.

## 3. Como Subir o Sistema

### Via Scripts (Recomendado)
Para subir a stack otimizada para produção local:
```bash
./scripts/local-production-up.sh
```

### Via Makefile
```bash
make up
```

### Via Docker Compose
```bash
docker compose up -d --build
```

## 4. Como Validar o Sistema

Para garantir que todos os serviços estão operando corretamente, execute a suíte de validação completa:

### Via Makefile
```bash
make validate-local-production
```

### Via Script
```bash
./scripts/validate-local-production-full.sh
```

## 5. URLs Principais

### API e Status
- **Health Check:** `http://localhost:18080/health`
- **Ready Check:** `http://localhost:18080/ready`
- **Status Geral:** `http://localhost:18080/status`
- **Métricas (Prometheus):** `http://localhost:18080/metrics`

### Interfaces (UIs)
- **Landing Page:** `http://localhost:18080/`
- **Portal do Cliente:** `http://localhost:18080/client-portal`
- **Admin Dashboard:** `http://localhost:18080/admin-dashboard`
- **Admin Lab (Gestão Operacional):** `http://localhost:18080/admin-lab`

### Endpoints OpenAI
- **Listar Modelos:** `GET http://localhost:18080/v1/models`
- **Chat Completions:** `POST http://localhost:18080/v1/chat/completions`

## 6. Como Criar Cliente Local

### Via Script
Use o script auxiliar para criar um cliente e já associá-lo a um plano:
```bash
./scripts/create-customer-demo.sh nome-do-cliente "Descrição do Cliente" free
```

### Via Admin API
```bash
curl -fsS http://localhost:18080/admin/clients \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "cliente-x",
    "description": "novo cliente local",
    "rate_limit_per_minute": 10
  }'
```

## 7. Como Criar API Key Local

### Via Admin API
1. Obtenha o `client_id` do cliente criado.
2. Gere a chave:
```bash
curl -fsS http://localhost:18080/admin/api-keys \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"client_id":"UUID_DO_CLIENTE","name":"minha-chave"}'
```
**Atenção:** A API Key é exibida apenas uma vez em texto claro. **Nunca commite API Keys no repositório.**

## 8. Como Testar Chat

### Teste Simples (Sem Stream)
```bash
curl -X POST http://localhost:18080/v1/chat/completions \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "unsloth/gemma-4-E4B-it-GGUF",
    "messages": [{"role": "user", "content": "Olá, quem é você?"}]
  }'
```

### Teste de Streaming
```bash
./scripts/test-stream.sh
```
Ou via curl:
```bash
curl -N http://localhost:18080/v1/chat/completions \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "unsloth/gemma-4-E4B-it-GGUF",
    "messages": [{"role": "user", "content": "Conte uma piada longa."}],
    "stream": true
  }'
```

## 9. Como usar LM Studio

O sistema pode atuar como um proxy para o LM Studio se você quiser usar outros modelos localmente.

1. Configure o LM Studio para ouvir em `0.0.0.0`.
2. No `.env.local`, defina:
   `LM_STUDIO_BASE_URL=http://192.168.101.1:1234/v1` (ajuste o IP do host).
3. Reinicie a stack.
4. Valide a conexão:
   ```bash
   ./scripts/test-lmstudio.sh
   ```
**Comportamento Offline:** Se o LM Studio estiver offline, as requisições para backends roteados para ele falharão com 503 Service Unavailable.

## 10. Como Usar RAG Local

### Upload de Documento
```bash
curl -X POST http://localhost:18080/v1/rag/files \
  -H "Authorization: Bearer ${API_KEY}" \
  -F "file=@meu_documento.pdf"
```

### Consultar (Query)
```bash
curl -X POST http://localhost:18080/v1/rag/query \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "O que o documento diz sobre X?",
    "file_ids": ["UUID_DO_ARQUIVO"]
  }'
```

### Limpeza Segura
O isolamento por cliente garante que um cliente não veja os dados de outro. Para apagar tudo:
```bash
docker compose down -v
```

## 11. Como Usar Billing Local/Manual

Como não há PSP real, o fluxo de faturamento é manual.

1. **Gerar Invoice:** `./scripts/generate-invoices.sh`
2. **Simular Overdue:** As faturas vencem automaticamente após `BILLING_DUE_DAYS`.
3. **Suspender Cliente:** `./scripts/suspend-client.sh UUID_DO_CLIENTE`
4. **Marcar como Pago:** `./scripts/mark-invoice-paid.sh UUID_DA_FATURA ref-pagamento`
5. **Desbloquear Cliente:** `./scripts/unsuspend-client.sh UUID_DO_CLIENTE`

## 12. Como Acessar Logs

### Todos os serviços
```bash
docker compose logs -f
```

### Serviço específico
```bash
docker compose logs -f control-plane
docker compose logs -f data-plane-gemma
```

### Artefatos de Validação
Após rodar `validate-local-production-full.sh`, os logs detalhados ficam em:
`artifacts/local-production-validation/<timestamp>/`

## 13. Backup e Restore

### Backup
Gera um dump do banco de dados e salva o estado atual:
```bash
./scripts/backup-local.sh
```

### Restore
Restaura o banco a partir de um dump:
```bash
./scripts/restore-local.sh artifacts/backups/postgres_latest.dump
```

## 14. Como Criar Release Local

Para gerar um manifesto da versão atual para deploy:
```bash
./scripts/release-local-production.sh
```
Isso gerará os arquivos em `releases/v<VERSION>/`.

## 15. Troubleshooting

| Problema | Causa Provável | Solução |
| :--- | :--- | :--- |
| Porta 18080 ocupada | Outro processo usando a porta | `lsof -i :18080` e mate o processo ou mude `HOST_PORT` no `.env` |
| Redis/Postgres Offline | Erro no startup do Docker | `docker compose logs redis` ou `postgres` |
| LM Studio Offline | LM Studio não iniciado no host | Inicie o LM Studio e verifique o IP/Porta |
| Modelo Offline | Data plane não carregou GGUF | Verifique `MODEL_FILE` e `docker compose logs data-plane-gemma` |
| Erro 401 | API Key inválida ou ausente | Verifique o header `Authorization: Bearer sk-...` |
| Erro 402/403 | Cliente suspenso/inadimplente | Verifique o `billing_status` no Admin Dashboard e pague a fatura |
| RAG não indexa | Worker offline ou PDF corrompido | Verifique `docker compose logs control-plane-worker` |
| Admin Lab vazio | Falha na comunicação com API | Verifique o console do navegador e o `ADMIN_TOKEN` |

## 16. Limpeza segura de dados RAG locais

O diretório `data/rag_uploads/` pode acumular muitos documentos de teste. Use o script de limpeza segura para liberar espaço sem afetar modelos ou código.

### Exemplos de uso:

- **Apenas mostrar o que seria apagado (Dry Run):**
  ```bash
  ./scripts/clean-rag-local-data.sh --dry-run
  ```

- **Limpar arquivos mais antigos que 7 dias:**
  ```bash
  ./scripts/clean-rag-local-data.sh --older-than-days 7 --yes
  ```

- **Limpar dados de um cliente específico:**
  ```bash
  ./scripts/clean-rag-local-data.sh --client-id UUID_DO_CLIENTE --yes
  ```

- **Limpar tudo (Arquivos, Artifacts e Metadados do Banco):**
  ```bash
  ./scripts/clean-rag-local-data.sh --include-artifacts --reset-db-metadata --yes
  ```

**Importante:** O script protege automaticamente diretórios críticos como `models/`, `scripts/`, `docs/` e arquivos `.gguf`. Sem a flag `--yes`, ele pedirá confirmação manual digitando `DELETE LOCAL RAG DATA`.

