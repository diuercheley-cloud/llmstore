---
owner: platform-ops
status: consolidated
---

# Comandos de Captura de Screenshots

## Captura Automática (Recomendado)

```bash
./scripts/dev/prepare-demo-screenshots-local.sh
```

O script detecta automaticamente se Playwright/Chromium está disponível e captura todas as telas.

## Captura Manual com Playwright

### Instalação

```bash
pip install playwright
playwright install chromium
```

### Comandos Individuais

```bash
# Landing Page
playwright screenshot --viewport-size="1280,800" http://localhost:18080/ artifacts/demo-screenshots/landing-page.png

# Capabilities
playwright screenshot --viewport-size="1280,800" http://localhost:18080/capabilities artifacts/demo-screenshots/capabilities.png

# Admin Dashboard (requer ADMIN_TOKEN)
playwright screenshot --viewport-size="1280,800" http://localhost:18080/admin-dashboard artifacts/demo-screenshots/admin-dashboard.png

# Admin Lab
playwright screenshot --viewport-size="1280,800" http://localhost:18080/admin-lab artifacts/demo-screenshots/admin-lab.png

# Client Portal
playwright screenshot --viewport-size="1280,800" http://localhost:18080/client-portal artifacts/demo-screenshots/client-portal.png

# Pricing
playwright screenshot --viewport-size="1280,800" http://localhost:18080/pricing artifacts/demo-screenshots/pricing.png
```

### Comandos via API (Terminal)

```bash
# API Chat Completion
curl -N http://localhost:18080/v1/chat/completions \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"default","messages":[{"role":"user","content":"Teste"}],"max_tokens":128}' > artifacts/demo-screenshots/api-chat-response.json 2>&1

# RAG Query
curl -s -X POST "http://localhost:18080/v1/rag/query" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"question":"Qual a política de retenção?"}' > artifacts/demo-screenshots/rag-response.json 2>&1

# TTS
curl -s -X POST "http://localhost:18080/pocket-tts/tts" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"text":"Mensagem de voz local."}' -o artifacts/demo-screenshots/tts-demo.wav 2>&1
```

### Relatórios (Saída em Arquivo)

```bash
./scripts/validators/security-report-local.sh 2>&1 | tee artifacts/demo-screenshots/security-report.txt
./scripts/dev/production-readiness-local.sh 2>&1 | tee artifacts/demo-screenshots/production-readiness.txt
make meeting-ready 2>&1 | tee artifacts/demo-screenshots/meeting-ready.txt
make generate-proposal COMPANY_NAME="Cliente Demo" 2>&1 | tee artifacts/demo-screenshots/proposal-generation.txt
```

## Captura com Ferramentas Alternativas

### Firefox Developer Edition
```bash
firefox --screenshot artifacts/demo-screenshots/landing-page.png http://localhost:18080/
```

### Chrome Headless
```bash
google-chrome --headless --screenshot=artifacts/demo-screenshots/landing-page.png --window-size=1280,800 http://localhost:18080/
```

## Organização dos Arquivos

```
artifacts/demo-screenshots/<timestamp>/
├── landing-page.png
├── capabilities.png
├── admin-dashboard.png
├── admin-lab.png
├── client-portal.png
├── pricing.png
├── api-chat-response.json
├── rag-response.json
├── tts-demo.wav
├── security-report.txt
├── production-readiness.txt
├── meeting-ready.txt
├── proposal-generation.txt
└── capture-plan.md
```
