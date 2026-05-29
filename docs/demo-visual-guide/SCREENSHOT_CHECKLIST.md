---
owner: platform-ops
status: consolidated
---

# Screenshot Checklist

## Instruções

Para cada tela abaixo, capture uma imagem demonstrando a funcionalidade descrita. Use o script `scripts/prepare-demo-screenshots-local.sh` para captura automatizada, ou capture manualmente com ferramenta de sua escolha.

Coloque os screenshots em `artifacts/demo-screenshots/<timestamp>/`.

## Checklist

- [ ] **1. Landing Page** (`/`)
  - Mostrar hero section com nome do produto e CTA
  - Verificar se dados sensíveis não aparecem

- [ ] **2. Capabilities Page** (`/capabilities`)
  - Mostrar tabela de capacidades com status (Suportado/Parcial/Não suportado)
  - Verificar se limitações PSP/PIX aparecem explicitamente

- [ ] **3. Client Portal** (`/client-portal`)
  - Mostrar dashboard de consumo do cliente
  - Mostrar seção de API Keys
  - Mostrar seção de faturas
  - Verificar se ADMIN_TOKEN não está exposto

- [ ] **4. Admin Dashboard** (`/admin-dashboard`)
  - Mostrar visão geral com saúde dos serviços
  - Mostrar lista de clientes
  - Mostrar gráficos de uso/latência (se disponíveis)

- [ ] **5. Admin Lab** (`/admin-lab`)
  - Mostrar aba de Modelos
  - Mostrar aba Financeiro/Faturas
  - Mostrar health check profundo

- [ ] **6. System Control Center** (se existir)
  - Mostrar status geral do sistema

- [ ] **7. Sales / Leads**
  - Mostrar pipeline de vendas
  - Mostrar detalhes de um lead demo

- [ ] **8. Pricing / Plans**
  - Mostrar tabela de planos (Free, Basic, Pro, Enterprise)

- [ ] **9. RAG Demo**
  - Mostrar requisição RAG (`POST /v1/rag/query`)
  - Mostrar resposta com contexto

- [ ] **10. TTS Demo**
  - Mostrar requisição TTS (`POST /pocket-tts/tts`)
  - Mostrar áudio gerado (comprovar existência do arquivo)

- [ ] **11. API Examples**
  - Mostrar chamada `/v1/chat/completions` funcionando
  - Mostrar listagem de modelos (`/v1/models`)

- [ ] **12. Security Report**
  - Mostrar relatório de segurança gerado
  - Verificar se não expõe secrets reais

- [ ] **13. Production Readiness**
  - Mostrar relatório de readiness

- [ ] **14. Meeting Ready Report**
  - Mostrar resultado do meeting-ready check

- [ ] **15. Proposal / Quote / SOW Output**
  - Mostrar proposta técnica gerada
  - Mostrar quote gerado
  - Mostrar SOW gerado

## Pós-captura

- [ ] Rodar `scripts/validate-demo-visual-guide.sh`
- [ ] Verificar se nenhuma imagem contém secrets reais
- [ ] Verificar se placeholders não contêm dados sensíveis
- [ ] Confirmar que `artifacts/demo-screenshots/` está no `.gitignore`
