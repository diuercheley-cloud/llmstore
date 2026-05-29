---
owner: platform-ops
status: consolidated
---

# Enterprise Audit Portal

O Enterprise Audit Portal expõe visibilidade segura para clientes enterprise acompanharem approval chains, evidence packages, attestations, exceptions, relatórios de auditoria e eventos financeiros/compliance sem sair do portal do cliente.

## RBAC

- `enterprise_readonly`: consulta approval chains, evidence packages, attestations, exceptions, relatórios salvos e access logs.
- `enterprise_finance`: consulta visibilidade financeira do tenant e pode exportar/download de `financial_summary`.
- `enterprise_auditor`: consulta artefatos de auditoria do tenant e pode exportar/download relatórios de auditoria.
- `enterprise_admin`: acesso completo ao escopo do tenant.

Os papéis podem ser atribuídos via `scopes_json` da API key ou metadados do cliente (`enterprise_portal_roles` / `enterprise_portal_role`).

## Tenant Isolation

- Toda consulta filtra por `client_id`.
- Recursos sem `client_id` não são exibidos no portal enterprise.
- Downloads validam ownership com `validate_portal_resource_access(...)`.
- Acesso cross-tenant retorna `404` para reduzir enumeração.

## Reports

Endpoints:

- `GET /portal/audit/approval-chains`
- `GET /portal/audit/evidence-packages`
- `GET /portal/audit/attestations`
- `GET /portal/audit/exceptions`
- `GET /portal/audit/reports`
- `POST /portal/audit/reports/generate`
- `GET /portal/audit/reports/{id}/download`
- `GET /portal/audit/access-logs`

Tipos de relatório:

- `audit`
- `evidence`
- `approval_chain`
- `attestation`
- `exception`
- `financial_summary`

Formatos de export:

- `json`
- `csv`
- `html`
- `pdf` opcional quando `COMMERCIAL_ENTERPRISE_AUDIT_EXPORT_PDF_ENABLED=true`

Todos os exports recebem:

- sanitização de payload
- watermark `CONFIDENTIAL ENTERPRISE AUDIT EXPORT`
- `immutable_hash`

## Access Logs

Toda ação abaixo gera `CommercialPortalAuditAccessLog`:

- `view`
- `export`
- `download`
- `search`
- `filter`

Campos sensíveis:

- IP é mascarado parcialmente
- `user_agent` é sanitizado
- `metadata_json` e `filters_json` passam por sanitização

## Compliance Visibility

O relatório consolidado pode incluir:

- approval chains
- evidence packages
- attestations
- exceptions
- financial audit events
- reconciliation records
- disputes
- QoS billing
- invoices

## Configurações

- `COMMERCIAL_ENTERPRISE_AUDIT_PORTAL_ENABLED=true`
- `COMMERCIAL_ENTERPRISE_AUDIT_EXPORT_PDF_ENABLED=false`
- `COMMERCIAL_ENTERPRISE_AUDIT_LOG_RETENTION_DAYS=365`
- `COMMERCIAL_ENTERPRISE_AUDIT_REQUIRE_RBAC=true`

## Limitações

- Não há dependência de IdP externo.
- `actor_email` é opcional e pode ser informado pelo header `X-Portal-Actor-Email`.
- Registros de compliance legados sem `client_id` não aparecem no portal enterprise.
- PDF depende de `weasyprint` disponível no runtime.
