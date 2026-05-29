---
owner: platform-ops
status: consolidated
---

# Data Boundaries and Multi-Tenancy

O isolamento de dados é um pilar fundamental da arquitetura de agentes da plataforma.

## Mecanismos de Isolamento

### Camada de Banco de Dados
Todas as tabelas de memória (`agent_memory_items`, `agent_memory_access_events`, etc.) possuem uma coluna `tenant_id`.

### Camada de Serviço
O `AgentMemoryService` exige um `tenant_id` em todos os métodos de leitura e escrita. Consultas sem o filtro de tenant são proibidas programaticamente.

### Camada de API
Os endpoints administrativos validam se o administrador tem permissão para acessar o `tenant_id` solicitado. Endpoints de agentes usam o `X-Tenant-ID` verificado pela autenticação/sessão.

## Prevenção de Vazamento (Cross-Tenant)

- **Content Hashing**: O hash de conteúdo é gerado por tenant, impedindo que colisões de hash (raras) revelem a existência de conteúdos idênticos em outros inquilinos.
- **Access Auditing**: O log de acesso registra tentativas de leitura, permitindo detectar anomalias ou tentativas de acesso não autorizado.
- **Redaction e Encryption**: Mesmo que houvesse uma falha de isolamento no DB, os dados persistidos podem estar mascarados ou criptografados com chaves específicas por inquilino.
