# SaaS Deployment Mode

Este documento descreve o funcionamento e os requisitos do modo de implantação **SaaS** do LLM Inference Stack.

## Visão Geral

O modo SaaS (`DEPLOYMENT_MODE=saas`) é projetado para implantações multi-tenant expostas publicamente, onde segurança, isolamento e controle de custos são críticos.

Diferente do modo `appliance` (focado em uso local ou privado), o modo SaaS impõe restrições rigorosas na inicialização e em tempo de execução.

## Requisitos de Segurança

Quando operando em modo SaaS, a stack exige:

1.  **ADMIN_TOKEN Forte**: Mínimo de 32 caracteres, incluindo letras maiúsculas, minúsculas e números.
2.  **CORS Explícito**: Não é permitido o uso de wildcard (`*`) em `CORS_ALLOW_ORIGINS`. Você deve listar os domínios permitidos.
3.  **Bloqueio de Endpoints de Debug**: Caminhos como `/admin-lab`, `/admin/tests`, `/admin/readiness` e `/admin/security` são bloqueados automaticamente pelo middleware para evitar vazamento de informações de infraestrutura.
4.  **Rate Limit Global**: É aplicado um limite global de requisições (padrão 1000 req/min) para proteger o cluster de ataques de negação de serviço ou picos inesperados.
5.  **Secret Scan PASS**: A validação de prontidão (`production-readiness`) exige que o scan de segredos não encontre vazamentos em logs ou artefatos.

## Guardrails Financeiros

Para evitar custos inesperados com provedores cloud (OpenAI, Anthropic, etc.), o modo SaaS introduz limites diários:

-   `MAX_GLOBAL_PROVIDER_COST_PER_DAY_BRL`: Limite total de custo com provedores cloud para toda a stack por dia.
-   `MAX_CLIENT_PROVIDER_COST_PER_DAY_BRL`: Limite individual por cliente.

**Comportamento quando o limite é atingido:**
-   O uso de Cloud Providers é bloqueado para novas requisições.
-   A stack tenta automaticamente o **fallback local** (se configurado).
-   Se não houver fallback local disponível, a requisição falha com erro informativo.

## Multi-tenancy e Isolamento

O isolamento é reforçado em todos os níveis:
-   **Inference**: Filtros rigorosos por `client_id` na seleção de rotas.
-   **RAG**: Documentos e chunks são isolados por cliente.
-   **Billing**: Invoices, carteiras e transações são estritamente privadas ao cliente autenticado.

## Observabilidade SaaS

Administradores podem monitorar a saúde da operação SaaS via endpoint:
`GET /admin/saas/overview`

Este endpoint retorna:
-   Total de clientes e clientes ativos.
-   Volume de requisições do dia.
-   Custo de provedor acumulado hoje.
-   Receita e margem estimada.
-   Status dos guardrails (se houve bloqueio por custo).

## Checklist de Produção SaaS

Antes de abrir para o público:
- [ ] Definir `DEPLOYMENT_MODE=saas`.
- [ ] Gerar `ADMIN_TOKEN` de 32+ chars.
- [ ] Configurar `CORS_ALLOW_ORIGINS` com seus domínios de frontend.
- [ ] Configurar `MAX_GLOBAL_PROVIDER_COST_PER_DAY_BRL` de acordo com seu orçamento.
- [ ] Executar `make production-readiness` e garantir score **READY**.
