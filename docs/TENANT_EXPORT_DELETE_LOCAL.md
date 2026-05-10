# Exportação e Deleção de Tenant (Local)

Este guia descreve como realizar a exportação segura de dados de um cliente (tenant) e como proceder com a deleção segura de seus dados no `llm-inference-stack`.

## 1. Exportação de Tenant

A exportação serve para suporte, auditoria, migração ou backup seletivo.

### Script de Exportação
Utilize o script `scripts/export-client-local.sh`.

```bash
# Exportar por ID
./scripts/export-client-local.sh --client-id UUID

# Exportar por Email
./scripts/export-client-local.sh --email user@example.com

# Exportar incluindo arquivos RAG e TTS
./scripts/export-client-local.sh --client-id UUID --include-rag-files --include-tts-files
```

### O que é exportado por padrão:
- Metadados do cliente (nome, descrição, status)
- Plano de faturamento associado
- API Keys (redigidas: apenas ID, prefixo e datas; o valor completo nunca é exportado)
- Resumo de uso (Usage Records), incluindo Chat, Embeddings e Responses
- Faturas e pagamentos locais
- Metadados de documentos RAG e eventos de uso de RAG
- Metadados de arquivos TTS e eventos de uso de TTS
- Eventos de auditoria/segurança relacionados ao cliente
- Políticas de acesso a modelos
- Metadados da própria exportação

### Segurança da Exportação
- **Redaction:** Emails e nomes completos são mascarados por padrão. Chaves de API nunca são exportadas na íntegra.
- **Git Ignore:** A pasta `exports/` está no `.gitignore`. Nunca force o commit destes dados.
- **Validação Automática:** O script roda `check-secrets.sh` no export gerado. Se encontrar algo suspeito, marca o export como `.unsafe`.

---

## 2. Deleção e Anonimização Segura

Para realizar o offboarding completo e seguro de um cliente, utilize o script `scripts/delete-client-local.sh`.

### Deleção Segura (Purge)
Remove os dados do banco de dados e, opcionalmente, os arquivos físicos.

```bash
# Deleção completa com confirmação interativa
./scripts/delete-client-local.sh --client-id UUID --delete-rag-files --delete-tts-files --delete-invoices

# Deleção automática (CI/CD) com export obrigatório prévio
./scripts/delete-client-local.sh --client-id UUID --yes --require-export --delete-rag-files
```

### Anonimização
Mantém os registros (como faturas para contabilidade) mas remove todas as informações de identificação pessoal (PII).

```bash
./scripts/delete-client-local.sh --client-id UUID --anonymize-instead --yes
```

### Opções do Script:
- `--client-id UUID`: ID do cliente.
- `--email EMAIL`: Nome/Email para resolução de ID.
- `--dry-run`: Lista o que será feito sem alterar nada.
- `--yes`: Pula a confirmação interativa.
- `--require-export`: Exige que exista um export recente (ou cria um na hora).
- `--delete-rag-files`: Remove arquivos físicos de RAG.
- `--delete-tts-files`: Remove arquivos físicos de TTS (.wav).
- `--delete-invoices`: Remove faturas (padrão é preservar/anonimizar).
- `--anonymize-instead`: Modo de anonimização.
- `--allow-demo-client`: Permite apagar o `demo-client`.

### Segurança e Auditoria:
- **Confirmação Forte:** Sem `--yes`, exige digitar `DELETE CLIENT <UUID>`.
- **Proteção de Demo:** O script bloqueia a deleção do cliente demo por padrão.
- **Relatório de Deleção:** Um relatório JSON é gerado em `artifacts/client-deletions/`.
- **Eventos de Auditoria:** São registrados eventos `client.delete.requested`, `client.deleted` ou `client.anonymized` na tabela de segurança.

## 3. Fluxo Recomendado de Offboarding
1. Execute o script de deleção com export obrigatório:
   ```bash
   ./scripts/delete-client-local.sh --client-id UUID --require-export --delete-rag-files --delete-tts-files
   ```
2. O script irá:
   - Gerar o export em `exports/clients/UUID/`.
   - Validar o export contra segredos vazados.
   - Solicitar confirmação.
   - Chamar a API de Purge (Banco de dados).
   - Remover arquivos físicos do disco.
   - Gerar um relatório final em `artifacts/client-deletions/`.
