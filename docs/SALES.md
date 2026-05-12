# Sales CRM Local

Este módulo fornece um CRM simples e local para gestão de leads e oportunidades comerciais, permitindo o acompanhamento do funil de vendas sem depender de serviços externos ou expor dados na internet.

## Funcionalidades

- **Gestão de Leads**: Cadastro e edição de empresas, contatos e segmentos.
- **Funil de Vendas**: Acompanhamento de estágios (Novo, Contatado, Demo Agendada, Proposta Enviada, Negociação, Ganho, Perdido).
- **Timeline de Notas**: Histórico de interações e mudanças de estágio.
- **Estimativa de Valor**: Valor potencial de cada oportunidade em BRL.
- **Next Follow-up**: Agendamento da próxima ação de acompanhamento.
- **Privacidade Total**: Todos os dados são armazenados localmente no banco de dados do Control Plane.

## API Administrativa

Todos os endpoints requerem `X-Admin-Token`.

- `GET /admin/sales/leads`: Lista leads (filtro opcional por `status`).
- `POST /admin/sales/leads`: Cria novo lead.
- `GET /admin/sales/leads/{id}`: Detalhes do lead e notas.
- `PATCH /admin/sales/leads/{id}`: Atualiza dados do lead.
- `DELETE /admin/sales/leads/{id}`: Remove um lead.
- `POST /admin/sales/leads/{id}/notes`: Adiciona uma nota.
- `POST /admin/sales/leads/{id}/advance-stage`: Avança o estágio com nota automática.

## Interface (Admin Dashboard)

Acesse o **Admin Dashboard** e localize a seção **Sales / Leads**. Lá você poderá visualizar o funil, adicionar novos leads e gerenciar o status de cada um.

## Dados de Demonstração

Para popular o CRM com dados fictícios de exemplo:

```bash
make sales-seed
```

## Geração de Propostas

Você pode gerar uma proposta comercial personalizada em Markdown (e opcionalmente PDF) a partir de um lead existente no CRM ou informando os dados manualmente.

### Comandos principais

**Gerar para um lead do CRM:**
```bash
make generate-proposal LEAD_ID=lead-uuid-aqui
```

**Gerar informando dados manuais:**
```bash
./scripts/generate-client-proposal.sh --company-name "Minha Empresa" --contact-name "João Silva" --plan "Pro"
```

As propostas são geradas em `artifacts/proposals/<timestamp>/` e incluem o arquivo `.md` e um `proposal-metadata.json`.

### Configuração de Preços e Padrões
Edite ou crie `config/sales-proposal.json` para definir os valores padrão de setup, mensalidade, moeda e escopo. Utilize `config/sales-proposal.example.json` como base.


### Gerador de Orçamento Local (v1.6.5)

Para demonstrações rápidas, utilize o script local ou a interface no Admin Dashboard.
Os valores são configuráveis em `config/pricing.local.json`.

**Via CLI:**
```bash
./scripts/generate-local-quote.sh --company-name "Nome da Empresa" --plan Pro --rag
```

## Contratos e SOW

Templates de contrato e SOW (Statement of Work) para implantação local estão disponíveis em `contracts/`.

**Gerar SOW personalizado:**
```bash
./scripts/generate-sow-local.sh --company-name "Nome da Empresa" --project-name "Local AI Appliance" --plan Pro
```

**Validar templates de contrato:**
```bash
./scripts/validate-contract-templates-local.sh
```

**AVISO:** Todos os templates exigem revisão jurídica obrigatória antes da assinatura. Consulte `contracts/README.md` para detalhes.

### Relatório Mensal por Cliente

Gere relatórios mensais de uso, faturamento e recomendações para clientes:

```bash
# Via CLI
./scripts/generate-client-monthly-report.sh --email cliente@exemplo.com --month 2026-05

# Com ID do cliente (busca dados da API)
./scripts/generate-client-monthly-report.sh --client-id <uuid> --month 2026-05

# Via Make
make monthly-report-demo

# Endpoint Admin (preview via API)
GET /admin/sales/monthly-report-preview?client_id=<uuid>&month=2026-05
Headers: X-Admin-Token: <token>
```

Os relatórios são gerados em `artifacts/monthly-reports/` (ignorados pelo Git).

## White-Label / Branding

O sistema suporta personalização de marca (nome do produto, cores, textos) via arquivo de configuração. Consulte `docs/WHITE_LABEL_LOCAL.md` para detalhes.

```bash
cp config/branding.example.json config/branding.local.json
# Edite o arquivo e reinicie o stack
make validate-white-label
```
