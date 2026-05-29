---
owner: platform-ops
status: consolidated
---

# Fresh Machine / Clean WSL Validation

## Objetivo

Este documento define o roteiro e checklist para validar que o **LLM Inference Stack** pode ser instalado e executado em uma máquina nova / WSL limpo, sem dependências prévias além das documentadas.

A validação é **offline-first**: não depende de internet para testes obrigatórios, não baixa modelos automaticamente e não expõe secrets.

## Pré-requisitos

- Windows 10/11 com WSL2 habilitado **ou** Linux (Ubuntu 22.04+)
- Docker Desktop (WSL2 backend) **ou** Docker Engine + docker compose plugin
- NVIDIA GPU com driver CUDA 12.x (opcional — fallback CPU funciona)
- Mínimo: 8 GB RAM, 20 GB disco livre

## Como preparar WSL limpo

```bash
# No PowerShell (Admin):
wsl --install -d Ubuntu-22.04
wsl --set-default-version 2

# Dentro do WSL:
sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io docker-compose-v2 git curl jq python3 python3-venv
```

### Verificar GPU no WSL2

```bash
nvidia-smi
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

Se o segundo comando falhar, instale o NVIDIA Container Toolkit:
```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt update && sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

## Como clonar repositório

```bash
# Via release bundle (recomendado para cliente final)
tar -xzf llm-inference-stack-v1.7.0.tar.gz
cd llm-inference-stack-v1.7.0

# Via git (operadores internos)
git clone <url-do-repositorio> llm-inference-stack
cd llm-inference-stack
git checkout feature/v1.7.1-post-release-polish
```

## Como configurar .env.local

```bash
cp .env.example .env.local
# Edite as variáveis obrigatórias:
# - ADMIN_TOKEN
# - POSTGRES_PASSWORD
# - MODEL_FILE (se tiver modelo)
vi .env.local
```

Configuração mínima para validação sem GPU (mock mode):
```bash
# No .env.local, garanta:
MODEL_MOCK_MODE=true
# ou mantenha LLAMA_N_GPU_LAYERS=0 para CPU-only
```

## Como copiar modelos GGUF

> **Nota:** O validador nunca baixa modelos automaticamente. O operador deve copiá-los manualmente.

```bash
# Copie o(s) arquivo(s) .gguf para o diretório models/
cp /caminho/para/seu-modelo-q4_0.gguf models/

# Verifique se o MODEL_FILE em .env.local corresponde ao nome do arquivo
grep MODEL_FILE .env.local
```

## Como rodar install-local-appliance.sh

```bash
# Dry-run primeiro
./scripts/install-local-appliance.sh --dry-run

# Instalação completa (com demo data)
./scripts/install-local-appliance.sh --with-demo

# Ou em modo headless
./scripts/install-local-appliance.sh --yes --with-demo --gpu
```

## Como rodar make customer-demo

```bash
# Modo rápido (valida sem recriar dados)
make customer-demo

# Modo completo (seed de dados, reset, validação completa)
make customer-demo-full
```

## Como validar security/readiness

```bash
# Health check básico
make health

# Relatório de segurança
make security

# Readiness check
make readiness

# Fresh machine readiness check
./scripts/fresh-machine-readiness-check.sh
```

## Como coletar logs

```bash
# Logs completos da stack
docker compose logs --no-color > debug_logs.txt

# Logs específicos
docker compose logs control-plane
docker compose logs data-plane-gemma

# Fresh machine check report
./scripts/fresh-machine-readiness-check.sh --dry-run --output-dir artifacts/fresh-machine-check
```

## Troubleshooting

| Problema | Causa provável | Solução |
|---|---|---|
| `docker: command not found` | Docker não instalado | Instale Docker Desktop ou docker.io |
| `nvidia-smi: command not found` | GPU não configurada | Verifique WSL2 + NVIDIA driver + Container Toolkit |
| `Permission denied` ao rodar scripts | Scripts sem permissão | `chmod +x scripts/*.sh` |
| `.env.local not found` | Ambiente não configurado | `cp .env.example .env.local` e edite |
| `No model file found` | Modelo GGUF ausente | Copie modelo para `models/` ou ative `MODEL_MOCK_MODE=true` |
| `Port 18080 already in use` | Conflito de porta | Configure porta alternativa via wizard |
| `check-secrets` falha | Secret real no código | Remova secrets de arquivos versionados |

## Checklist de Aceite

- [ ] WSL2 (se Windows) configurado corretamente
- [ ] Docker + docker compose funcionando
- [ ] git, curl, jq, python3 instalados
- [ ] .env.local criado a partir de .env.example
- [ ] .gitignore protege .env.local, models/, artifacts/
- [ ] Modelo GGUF presente em models/ OU MODAL_MOCK_MODE=true
- [ ] Scripts têm permissão de execução
- [ ] `fresh-machine-readiness-check.sh --dry-run` passa
- [ ] `validate-fresh-machine-docs.sh` passa
- [ ] `check-secrets.sh --all` passa
- [ ] `make install-local --dry-run` funciona
- [ ] Portas necessárias (18080, 5432, 6379) estão livres
- [ ] Relatório gerado em `artifacts/fresh-machine-check/<timestamp>/`
- [ ] Nenhum secret exposto em logs ou relatórios
- [ ] Nenhum modelo baixado automaticamente
- [ ] Nenhum PSP/PIX real está no escopo
