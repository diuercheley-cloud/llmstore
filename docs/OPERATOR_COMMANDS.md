---
owner: platform-ops
status: consolidated
---

# Guia de Comandos do Operador

Este documento descreve os comandos disponíveis via `Makefile` para operação e manutenção do **LLM Inference Stack** em ambiente local.

O `Makefile` serve como a interface oficial de entrada, abstraindo a complexidade dos scripts internos localizados em `scripts/`.

## Comandos Principais

### Inicialização e Execução

- `make first-run`: Realiza a configuração inicial completa, incluindo o download de modelos e carga de dados de demonstração. Use este comando na primeira vez que instalar o stack.
- `make up`: Inicia todos os serviços do stack em segundo plano (background).
- `make down`: Para todos os serviços e remove os containers.
- `make restart`: Reinicia o stack (executa `down` seguido de `up`).

### Monitoramento e Saúde

- `make status`: Exibe o estado atual dos containers do Docker.
- `make health`: Verifica a saúde dos principais endpoints da API (`/health`, `/ready`, `/status`).
- `make logs`: Exibe logs em tempo real. Use `SERVICE=nome_do_serviço` para filtrar logs de um serviço específico (ex: `make logs SERVICE=control-plane`).

### Validação e Segurança

- `make validate`: Executa uma bateria completa de testes de validação para garantir que o ambiente de produção local está operando corretamente.
- `make security`: Gera um relatório de segurança detalhado do ambiente local.
- `make readiness`: Verifica se o sistema atende aos requisitos mínimos de prontidão para operação (Production Readiness).
- `make check-secrets`: Varre a base de código em busca de segredos expostos acidentalmente.
- `make validate-control-center`: Valida a integridade do System Control Center e seus endpoints (Backend + UI).

### Manutenção e Backup

- `make backup`: Cria um backup completo dos dados (Banco de Dados, Snapshots .env). Os arquivos são salvos em `artifacts/backups-local/`.
- `make restore`: Restaura o sistema a partir de um backup. **Requer o parâmetro `BACKUP_DIR`**.
  - Exemplo: `make restore BACKUP_DIR=artifacts/backups-local/20260509-100000`
- `make clean-safe`: Realiza um dry-run da limpeza de dados antigos (retention). Não remove arquivos, apenas mostra o que seria removido.

### Ciclo de Vida e Atualização

- `make upgrade`: Aplica atualizações e migrações necessárias para a versão mais recente instalada.
- `make rollback`: Reverte a última atualização realizada.
- `make smoke`: Executa testes de fumaça (smoke tests) rápidos para validar a estabilidade após um upgrade.
- `make release`: Gera o pacote de release final (bundle).

### Testes e Performance

- `make benchmark`: Executa um teste de performance rápido (quick benchmark) em um modelo mock ou configurado.

---

## Cuidados e Recomendações

1. **Comandos Destrutivos**: `make down` remove containers, mas preserva volumes. `make restore` irá sobrescrever o banco de dados atual. Sempre faça um `make backup` antes de operações críticas.
2. **Ambiente Local**: Todos os comandos foram validados para execução em `localhost`.
3. **Logs**: Ao encontrar problemas, o comando `make logs` é sua primeira ferramenta de diagnóstico.

## Relação Makefile -> Scripts

O `Makefile` é apenas um wrapper. Se precisar de opções avançadas, você pode consultar e executar os scripts diretamente em `scripts/`.
Exemplo: `make up` chama `./scripts/deploy/up.sh`.

### Padrão de Erros Amigáveis
Todos os scripts principais agora utilizam o padrão de erros amigáveis. Caso um comando do `Makefile` falhe, a saída indicará um **Código de Erro** (ex: `DOCKER_NOT_RUNNING`).

Você pode encontrar a lista completa e instruções de resolução no [Catálogo de Códigos de Erro](OPERATOR_ERROR_CODES.md).
