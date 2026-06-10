---
owner: platform-ops
status: consolidated
---

# Catálogo de Códigos de Erro para Operadores

Este documento descreve os códigos de erro padronizados utilizados nos scripts do LLM Inference Stack.

## Códigos de Erro

| Código | O que aconteceu | Como resolver |
| :--- | :--- | :--- |
| **DOCKER_NOT_RUNNING** | O Docker não parece estar rodando no sistema. | Inicie o Docker Desktop ou execute `sudo systemctl start docker`. |
| **DOCKER_COMPOSE_MISSING** | O comando `docker compose` não foi encontrado. | Instale o Docker Compose seguindo a documentação oficial. |
| **PORT_IN_USE** | Uma porta necessária já está sendo utilizada por outro processo. | Identifique o processo que usa a porta e encerre-o, ou altere as portas no arquivo `.env`. |
| **ENV_MISSING** | O arquivo de configuração `.env` não foi encontrado. | Execute o assistente de configuração ou copie o `.env.example`. |
| **ENV_PERMISSION_UNSAFE** | As permissões do arquivo `.env` estão muito abertas. | Execute `chmod 600 .env` para proteger suas credenciais. |
| **ADMIN_TOKEN_DEFAULT** | O token de administrador ainda é o valor padrão "change-me". | Altere o `ADMIN_TOKEN` no seu arquivo `.env` para um valor seguro. |
| **MODEL_NOT_FOUND** | O modelo de linguagem solicitado não foi encontrado localmente. | Execute o script `scripts/deploy/download-model.sh` para baixar o modelo. |
| **GPU_NOT_DETECTED** | Nenhuma GPU NVIDIA compatível foi detectada, mas o modo GPU foi solicitado. | Verifique se os drivers NVIDIA e o NVIDIA Container Toolkit estão instalados. |
| **HEALTH_FAILED** | Um ou mais serviços falharam no teste de saúde (health check). | Verifique os logs dos containers com `docker compose logs`. |
| **READY_DEGRADED** | O sistema está rodando, mas alguns componentes secundários falharam. | Verifique o status detalhado com `scripts/dev/job-status.sh`. |
| **DB_UNAVAILABLE** | O banco de dados não está respondendo ou a conexão falhou. | Certifique-se de que o container do banco de dados está rodando e as credenciais no `.env` estão corretas. |
| **REDIS_UNAVAILABLE** | O serviço Redis (cache/fila) não está disponível. | Verifique se o container do Redis está rodando. |
| **MIGRATION_FAILED** | Falha ao aplicar as migrações de banco de dados. | Verifique os logs do control-plane para detalhes do erro SQL. |
| **VALIDATION_FAILED** | A validação de integridade do sistema falhou. | Corrija as inconsistências apontadas no detalhe técnico. |
| **SECURITY_FAILED** | Uma vulnerabilidade ou risco de segurança foi detectado. | Siga as recomendações do relatório de segurança gerado. |
| **RELEASE_METADATA_FAILED** | Falha ao gerar ou ler os metadados do bundle de release. | Verifique se o arquivo `VERSION` e o manifesto de release existem. |
| **SECRET_DETECTED** | Um segredo (API key, senha) foi detectado em um local inseguro (ex: logs). | Execute o script de limpeza de segredos: `scripts/backup/redact-local-sensitive-artifacts.sh`. |
| **BACKUP_FAILED** | Falha ao realizar o backup dos dados ou configurações. | Verifique o espaço em disco e as permissões da pasta de destino. |
| **RESTORE_FAILED** | Falha ao restaurar o sistema a partir de um backup. | Verifique se o arquivo de backup está íntegro e é compatível com a versão atual. |
| **UPGRADE_FAILED** | O processo de atualização para uma nova versão falhou. | Verifique os logs e considere realizar um rollback se o sistema estiver instável. |
| **ROLLBACK_FAILED** | Falha ao tentar retornar para a versão anterior. | Intervenção manual necessária; verifique o estado dos volumes do Docker. |
