# First Run Local

O script `first-run-local.sh` é desenhado para ajudar operadores técnicos a instanciar, configurar e validar o sistema localmente numa máquina nova (frequentemente com WSL2/Ubuntu) de maneira segura e automatizada.

## Uso

```bash
./scripts/first-run-local.sh [opções]
```

### Opções:

- `--with-demo`: Roda o ambiente demo (`demo-full-local.sh`) após levantar o sistema.
- `--skip-build`: Não faz o build de novas imagens Docker.
- `--cpu-only`: Força rodar em modo CPU.
- `--gpu`: Força rodar em modo GPU.
- `--base-url`: Especifica a URL base (padrão: `http://localhost:18080`).
- `--yes`: Pula prompts de confirmação.
- `--dry-run`: Exibe o que seria feito sem fazer.
- `--help`: Mostra a ajuda.

## O que ele faz?

1. **Detecção de Ambiente:** Verifica OS, WSL2, Docker, Compose, e GPU.
2. **Configuração:** Prepara `.env.local` preservando o original. Gera secrets como `ADMIN_TOKEN`.
3. **Modelos:** Checa por arquivos `.gguf` no diretório `models/`.
4. **Execução:** Sobe o docker-compose.
5. **Validação:** Roda `check-secrets.sh` e `validate-local-production-full.sh`.
6. **Relatório:** Gera evidências em `artifacts/first-run/`.

## Segurança

O script assegura que `.env.local` possua a permissão `600`, que os tokens não sejam exfiltrados nos logs de execução, e que segredos não sejam adicionados a repositórios git ou logs de output na tela desnecessariamente.
