---
owner: platform-ops
status: consolidated
---

# Guia Visual de Demonstração — Local AI Appliance

Este diretório contém o guia visual para demonstração comercial do **llm-inference-stack (Local AI Appliance)**.

## Propósito

Fornecer um roteiro visual padronizado para apresentações a clientes, com placeholders de screenshots, URLs de captura e instruções claras para obtenção das imagens em ambiente local.

## Estrutura

| Arquivo | Descrição |
|---------|-----------|
| `README.md` | Este arquivo — visão geral do guia visual |
| `SCREENSHOT_CHECKLIST.md` | Checklist de todas as telas que devem ser capturadas |
| `DEMO_VISUAL_FLOW.md` | Fluxo visual completo da demonstração |
| `CAPTURE_COMMANDS.md` | Comandos para captura de screenshots com Playwright/Chromium |
| `DEMO_STORYBOARD.md` | Storyboard com ordem, fala sugerida, objetivo e screenshot esperado |
| `placeholders/README.md` | Instruções para placeholders de screenshots |

## Screenshots

Screenshots **nunca devem ser commitados** com dados reais. Use placeholders sanitizados em `placeholders/`.

O script `scripts/dev/prepare-demo-screenshots-local.sh` gera screenshots automaticamente se Playwright/Chromium estiver disponível, ou cria um plano de captura manual.

## Comando Unico de Demo

```bash
make customer-demo
```

Prepara e valida a demo comercial completa. Relatório em `artifacts/customer-demo/<timestamp>/`.

## Telas Cobertas

- Landing Page (`/`)
- Capacidades (`/capabilities`)
- Client Portal (`/client-portal`)
- Admin Dashboard (`/admin-dashboard`)
- Admin Lab (`/admin-lab`)
- System Control Center
- Sales/Leads
- Pricing/Plans
- RAG demo
- TTS demo
- API examples
- Security Report
- Production Readiness
- Meeting Ready report
- Proposal/Quote/SOW output

## Limitações

- **PSP/PIX real**: Não disponível nesta versão. Billing é manual/local.
- **Dados reais**: Screenshots devem usar apenas dados fictícios.

## Segurança

- Nunca expor `ADMIN_TOKEN`, `API_KEY` ou dados reais em screenshots
- Usar placeholders sanitizados para versionamento
- Rodar `scripts/validators/validate-demo-visual-guide.sh` antes de qualquer commit
