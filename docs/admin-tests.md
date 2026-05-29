---
owner: platform-ops
status: consolidated
---

# Admin Tests Dashboard

A página `Admin Tests` é um painel de testes operacionais integrado ao LLM Inference Stack. Ela permite a execução rápida e visual de validações contra a API e componentes do sistema.

## Acesso
URL: [http://localhost:18080/admin-tests](http://localhost:18080/admin-tests)

A página exige autenticação por tokens na própria interface:
- **Admin Token**: Token administrativo, validado através de um sistema de Controle de Acesso Baseado em Papéis (RBAC). 
- **Client API Key**: Chave de API de um cliente normal (ex: `sk-local-...`) para testes de inferência no endpoint de chat.

## RBAC e Variáveis de Ambiente
O sistema suporta três níveis hierárquicos de acesso administrativo (`admin_read < admin_write < super_admin`). Configure as seguintes variáveis em `.env.local`:

- `ADMIN_SUPER_TOKEN`: Acesso total (pode bloquear/desbloquear usuários).
- `ADMIN_WRITE_TOKEN`: Acesso a alterações de quota, mas sem permissão de bloqueio.
- `ADMIN_READ_TOKEN`: Apenas leitura (saúde, recursos, validação).

*Nota: Se `ADMIN_SUPER_TOKEN` não for definido, o token `ADMIN_TOKEN` legado atuará automaticamente como Super Admin.*

## Proteções do Sistema

### 1. Auditoria Persistente
As ações sensíveis (Block, Unblock, Quota Set, Quota Reset, Quota Renew e Remoção de Override) são registradas automaticamente na tabela `admin_actions_log` do banco de dados, incluindo o cargo (Role), a ação, o IP e o status, mascarando chaves sensíveis para proteger o payload.

A interface possui uma tabela "Auditoria" onde admins com perfil Write/Super podem consultar os últimos 50 registros (`GET /admin/tests/audit`).

### 2. Quota Override Explícito
Se a funcionalidade de aplicar Quota Manual for usada (`POST /admin/tests/users/{userId}/quota/set`), isso será registrado como um **Override** explícito na tabela `user_quota_overrides`. Isso garante que o valor seja respeitado independentemente do `BillingPlan`.
A UI mostra claramente a comparação entre "Billing Plan Quota" e "Effective Limit (Override)". Os overrides podem ser removidos (retornando as contas aos limites padrão do plano).

### 3. Leitura Segura de NVIDIA-SMI
O endpoint de recursos do sistema executa comandos de detecção de GPU com *timeout* restrito a 1 segundo e tratamentos de erro abrangentes.
**Comportamento sem GPU:** Se você não tiver placas NVIDIA, ou a VM não conseguir ler, a API continuará retornando sucesso, identificando `gpu.available=false` sob a chave de justificativa.

### 4. Rate Limiting Administrativo
Para prevenir excessos acidentais na suíte de testes:
- **Super Admin:** Limite de 30 chamadas por minuto.
- **Admin Write:** Limite de 60 chamadas por minuto.
- **Admin Read:** Limite de 120 chamadas por minuto.

*Para ambientes CI/CD ou de desenvolvimento agressivo, você pode desabilitar essa limitação passando a env `ADMIN_TESTS_RATE_LIMIT_ENABLED=false`.*

## Funcionalidades e Endpoints da Suíte

### 1. Saúde Geral
- **Endpoint:** `GET /health` e `GET /ready`

### 2. Recursos do Servidor
- **Endpoint:** `GET /admin/tests/system/resources` (Role mínima: Read)
- Lê latência, CPU, memória e Load Average local e de GPU.

### 3. Teste de API
- **Endpoint:** `POST /v1/chat/completions` (Requer token Client válido)

### 4. Gestão de Usuário
- `GET /admin/tests/users/{userId}` (Role: Read)
- `POST /admin/tests/users/{userId}/block` (Role: Super Admin)
- `POST /admin/tests/users/{userId}/unblock` (Role: Super Admin)

### 5. Gestão de Quotas
- `POST /admin/tests/users/{userId}/quota/reset` (Role: Write)
- `POST /admin/tests/users/{userId}/quota/renew` (Role: Write)
- `POST /admin/tests/users/{userId}/quota/set` (Role: Write) - Cria override
- `DELETE /admin/tests/users/{userId}/quota/override` (Role: Write) - Remove override

### 6. Endpoint de Informações Autenticadas
- `GET /admin/tests/auth/whoami` (Retorna a validade do Token Admin e sua respectiva Role)
