# Política de Retenção Local

Este documento descreve a política de retenção para limpeza de dados temporários no ambiente `llm-inference-stack`.

## 1. Visão Geral

O sistema acumula diversos tipos de dados temporários durante a operação, validação e desenvolvimento. A política de retenção garante que o espaço em disco seja otimizado sem apagar dados críticos.

### O que é apagado (Candidatos):
- **RAG Uploads:** Documentos enviados para o sistema RAG.
- **TTS Audio:** Arquivos `.wav` gerados pelo serviço de voz.
- **Logs:** Arquivos no diretório `logs/`.
- **Artifacts:** Resultados de validações, benchmarks e testes de DR.
- **Backups:** Dumps de banco de dados antigos.

### O que NUNCA é apagado (Protegidos):
- **Modelos:** Arquivos `.gguf` e o diretório `models/`.
- **Código:** Diretórios `scripts/`, `src/`, `app/`, etc.
- **Configurações:** Arquivos `.env`, `.env.local`.
- **Documentação:** Diretório `docs/`.
- **Releases:** Diretório `releases/` (protegido por padrão).

## 2. Configuração

A política é controlada pelo arquivo `config/retention-example.json`. Você pode criar um `config/retention.local.json` para customizar os valores.

| Chave | Padrão | Descrição |
| :--- | :--- | :--- |
| `rag_uploads_retention_days` | `null` | Dias para manter arquivos RAG (null = não apagar por tempo). |
| `tts_audio_retention_days` | `7` | Dias para manter arquivos de áudio TTS. |
| `logs_retention_days` | `14` | Dias para manter arquivos de log. |
| `validation_artifacts_keep_last` | `10` | Quantas validações recentes manter em `artifacts/`. |
| `backups_keep_last` | `5` | Quantos backups recentes manter. |
| `releases_keep_all` | `true` | Se `true`, nunca apaga nada em `releases/`. |

## Limites e Cotas por Plano

O TTS agora é governado por planos de cobrança:

- **Enabled:** Se o TTS está habilitado para o plano.
- **Chars per Request:** Limite de caracteres por chamada única.
- **Daily/Monthly Quota:** Limite acumulado de caracteres por período.
- **Audio Retention:** Dias antes do áudio ser removido automaticamente (simulado localmente).
- **Max Files:** Limite de arquivos mantidos simultaneamente por cliente.

No fluxo de readiness:

- O probe autenticado de TTS remove o `.wav` temporário após a validação.
- Áudio temporário deve continuar em `artifacts/` ou outra área ignorada pelo Git.
- O check dedicado `./scripts/validate-tts-readiness-local.sh` confirma que não sobra `.wav` versionável.

## 3. Como Executar

### Dry Run (Simulação)
Sempre recomendado antes de executar a limpeza real:
```bash
./scripts/retention-local.sh --dry-run --section all
```

### Execução Real
```bash
./scripts/retention-local.sh --yes --section all
```

### Limpeza Seletiva
Você pode limpar apenas seções específicas:
```bash
./scripts/retention-local.sh --section logs
./scripts/retention-local.sh --section tts --older-than-days 1
```

Para uma limpeza focada em segurança (redação de dados sensíveis ou limpeza de relatórios de segurança), utilize:
```bash
./scripts/clean-sensitive-artifacts-local.sh --help
```

### Limpeza de Cliente Específico
Útil para RAG e TTS:
```bash
./scripts/retention-local.sh --section rag --client-id <UUID> --yes
```

## 4. Relatórios

Cada execução gera um relatório em `artifacts/retention/<timestamp>/`:
- `retention-report.json`: Dados estruturados para integração.
- `retention-report.md`: Resumo legível para humanos.

## 5. Segurança e Proteções

O script `retention-local.sh` possui várias camadas de segurança:
1. **Path Validation:** Impede a exclusão fora do projeto ou em caminhos raiz (`/`).
2. **Explicit Protection:** Lista de diretórios e extensões (como `.gguf`) que são ignorados.
3. **Dry Run Mode:** Modo padrão ou explícito que apenas lista candidatos.
4. **Confirmation:** Exige `--yes` para executar sem interação.
