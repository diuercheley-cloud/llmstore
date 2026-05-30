# Compliance Audit Pack

O Control Plane permite a geração de pacotes formais de auditoria para conformidade com padrões como **SOC2** e **ISO 27001**. 

## Objetivo

Transformar evidências operacionais esparsas em um conjunto estruturado, sanitizado e verificável que pode ser apresentado a auditores externos.

## Evidências Coletadas

O pacote de auditoria consolida as seguintes categorias de evidência:

- **Access Review**: Histórico de revisão de acessos e permissões.
- **Change Management**: Logs de aprovações de deployments e mudanças de infraestrutura.
- **Incident Response**: Registros de incidentes de segurança e planos de remediação.
- **Vulnerability Management**: Relatórios de scans de vulnerabilidades e status de correção.
- **Backup/Restore**: Logs de execução e testes de restauração de backups.
- **RBAC**: Configurações de controle de acesso baseadas em função por tenant.
- **Encryption**: Evidências de criptografia em repouso e em trânsito.

## Segurança e Integridade

- **Sanitização de Secrets**: O gerador de pacotes remove automaticamente chaves de API, senhas e tokens das evidências exportadas.
- **Checksums**: Cada pacote inclui um manifest com hashes SHA-256 de todos os arquivos para garantir a integridade dos dados coletados.
- **Timestamps**: Todas as evidências são carimbadas com o horário exato da coleta (UTC).

## Como Gerar

### Via API Admin

```http
POST /admin/compliance/audit-pack/generate?standard=soc2
```

### Via CLI Script

```bash
./scripts/generate-audit-pack.sh iso27001
```

Os pacotes gerados são armazenados em `compliance/audit-packs/{standard}/{uuid}/`.
