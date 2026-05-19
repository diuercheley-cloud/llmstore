# Preflight Checks

Antes de realizar qualquer deployment ou upgrade, é essencial garantir que o ambiente atende aos requisitos mínimos de sistema.

## Como Executar

Utilize o comando Makefile:

```bash
make preflight
```

Ou execute o script diretamente:

```bash
./scripts/preflight-check.sh
```

## Validações Realizadas

O script de preflight valida os seguintes itens:

1.  **Docker & Docker Compose**: Verifica se os binários estão instalados e funcionais.
2.  **GPU (NVIDIA)**: Detecta se drivers NVIDIA e `nvidia-smi` estão presentes (opcional para CPU-only, mas recomendado).
3.  **Disponibilidade de Portas**: Garante que a porta principal (default: 18080) não está em uso.
4.  **Espaço em Disco**: Exige no mínimo 10GB de espaço livre para containers e modelos.
5.  **Permissões**: Valida acesso de escrita nos diretórios `data/`, `models/`, `artifacts/` e `logs/`.
6.  **Configuração local**: Verifica a presença do arquivo `.env.local` e se senhas críticas (Postgres/Redis) foram definidas.
7.  **Segurança**: Faz uma varredura rápida em busca de segredos versionados ou expostos.

## Artefatos Gerados

Cada execução gera um relatório em markdown localizado em:
`artifacts/deployments/<timestamp>/preflight.md`
