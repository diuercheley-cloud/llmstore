# Security Hardening no CI/CD

## Prevenção de Exposição de Dados
- **check-secrets.sh**: Executado em todo PR para evitar commits acidentais de chaves.
- **Safety / Audit**: Auditoria automática de CVEs em dependências Python e Node.

## Isolamento de Ambiente
- Testes usam containers temporários de Postgres/Redis que são destruídos após a run.
- Nenhum acesso à rede interna da Pipolante é permitido durante o CI.
