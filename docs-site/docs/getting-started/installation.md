<!-- synced_from: docs/INSTALL.md -->

> Source of truth: `docs/INSTALL.md`

---
owner: platform-ops
status: consolidated
---

# Install

## Requisitos

- WSL2 ou Linux com `bash`
- Docker com plugin `docker compose`
- GPU NVIDIA configurada no host se quiser aceleração local
- `python3`, `curl`, `git`

## Instalação rápida

```bash
chmod +x scripts/deploy/install.sh scripts/deploy/first-run.sh scripts/dev/reset-dev.sh
./scripts/deploy/install.sh
```

O script:

- instala dependências base via `scripts/deploy/install-wsl-deps.sh`
- verifica `docker` e `docker compose`
- cria `.env.local` a partir de `.env.example` se necessário
- aplica permissão `chmod 600` no arquivo de ambiente local

## Primeira execução

```bash
HF_TOKEN=seu_token ./scripts/deploy/first-run.sh
```

O `scripts/deploy/first-run.sh` faz:

1. gera ou ajusta o arquivo `.env`
2. cria `ADMIN_TOKEN` e `POSTGRES_PASSWORD` locais se ainda estiverem nos valores padrão
3. valida GPU no host e no runtime Docker
4. baixa o modelo se ele ainda não existir em `models/`
5. sobe a stack
6. espera `ready`
7. garante um plano comercial default
8. cria um cliente demo com API key
9. imprime URLs e a API key do cliente demo

Por padrão:

- `PUBLIC_EXPOSURE=false`
- `CORS_ALLOW_ORIGINS=` vazio, sem liberar origens cross-origin

## Resultado esperado

Ao final do `scripts/deploy/first-run.sh`, você deve receber:

- URL base da stack
- URL do admin dashboard
- URL do client portal
- endpoint `/v1/chat/completions`
- API key do cliente demo

## Deploy SaaS em VPS

Use um dominio publico apontando para a VPS e rode:

```bash
export SERVER_NAME=api.seudominio.com
export LETSENCRYPT_EMAIL=ops@seudominio.com
sudo ./scripts/deploy/deploy-vps.sh
```

O script:

- atualiza `.env.prod` com dominio, email e `PUBLIC_BASE_URL`
- habilita `PUBLIC_EXPOSURE=true` e `PUBLIC_SIGNUP_ENABLED=true`
- sobe a stack em `STACK_MODE=prod`
- publica a borda com Caddy e HTTPS automatico

Rotas publicas esperadas:

- `/`
- `/pricing`
- `/signup`
- `/public/signup`
- `/client-portal`

## Instalação manual mínima

```bash
cp .env.example .env.local
./scripts/deploy/download-model.sh
./scripts/deploy/up.sh
./scripts/validators/validate-e2e.sh
```
